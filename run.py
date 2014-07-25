import os, re, sys, errno, traceback, datetime, string, urlparse, mimetypes
import requests
from bs4 import BeautifulSoup

from test_config import urls_to_crawl, file_extensions_list, mimetypes_list, request_timeout

fs_path_acceptable_chars = frozenset('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.-_')
files_written = 0            
errors_encountered = 0

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def download_file(current_url, data, encoding):
    """
    Data will either be data from an HTML file or None
    Encoding is the encoding of the data
    """
    if not data:
        get_response = requests.get(current_url, timeout=request_timeout)
        if get_response.status_code == requests.codes.ok:
            data = get_response.text
            encoding = get_response.encoding
        else:
            print "Received an invalid GET response"
    if data:
        url_parsed = urlparse.urlparse(current_url)
        netloc = url_parsed.netloc
        url_path = url_parsed.path.strip().lstrip("/")
        if url_path == "":
            filename = "root.file" 
            fs_path = netloc
        else:
            if url_path.endswith("/"): 
                url_path = url_path + "root.file" 
            url_path = netloc + "/" + url_path
            url_path = ''.join(c for c in url_path if c in fs_path_acceptable_chars)                
            url_path_list = url_path.split("/")
            filename = url_path_list.pop()
            filename = filename[:249] + ".file" # Most systems have a 255 char limit on filenames
            fs_path = "/".join(url_path_list)            
        fs_path = os.path.join( output_dir, fs_path)
        mkdir_p(fs_path)
        filepath = os.path.join(fs_path, filename)
        print "Writing file: ", filepath
        with open(filepath, 'w') as f:
            f.write( data.encode(encoding) )
        global files_written
        files_written += 1        
        
def add_new_urls(current_url, html):
    parsed_html = BeautifulSoup(html)
    for tag in parsed_html.findAll('a', href=True):
        href = tag['href'].strip() # Stripping handles <a href=" http...
        anchor_index = href.rfind("#") 
        if anchor_index != -1:
            href = href[:anchor_index] # We don't care about anchors
        if href:
            href_absolute_url = urlparse.urljoin(current_url, href)
            if follow_links_containing in href_absolute_url and href_absolute_url not in all_urls:
                urls_to_visit.append(href_absolute_url)
                all_urls.append(href_absolute_url)

def crawl_url():
    print "\n* NEW CRAWLING SESSION FOR CONFIG URL: %s *\n" % seed_url

    while len(urls_to_visit) > 0:
        current_url = urls_to_visit.pop(0)
        try:
            html_data = None
            met_mimetype_criteria = False
            met_file_extension_criteria = False                                        
            print "\nProcessing URL: %s\n" % current_url
            # Look for a valid head response from the URL
            head_response = requests.head(current_url, allow_redirects=True, timeout=request_timeout)
            if not head_response.status_code == requests.codes.ok:
                print "Received an invalid HEAD response"
            else:
                #current_url = head_response.url # In case we got a redirect
                head_content_type = head_response.headers.get('content-type')
                # If we found an HTML file, grab all the links
                if 'text/html' in head_content_type:
                    get_response = requests.get(current_url, timeout=request_timeout)
                    if get_response.status_code == requests.codes.ok:
                        html_data = get_response.text
                        encoding = get_response.encoding                    
                        add_new_urls(current_url, html_data)
                    else:
                        print "Received an invalid GET response"
                # Check if we should download files with this mimetype or extension
                for mimetype in mimetypes_list:
                    if mimetype in head_content_type:
                        met_mimetype_criteria = True
                if not met_mimetype_criteria:
                    for file_extension in file_extensions_list:
                        if file_extension in current_url: # This could be swapped for urlparse(current_url).path...[-1]
                            met_file_extension_criteria = True                
                # Check if we should download this file based on potential regex restrictions, only if it passes the mimetype or extension tests
                if met_mimetype_criteria or met_file_extension_criteria:
                    if not using_regex_filters:
                        download_file(current_url, html_data, encoding)
                    else:
                        for regex_filter in regex_filters:
                            if regex_filter.search(current_url):
                                download_file(current_url, html_data, encoding)
                                break
            print "Files Found: %d  Remaining: %d  Written: %d  Operational Errors: %d" % ( len(all_urls), len(urls_to_visit), files_written, errors_encountered )
        except:
            global errors_encountered
            errors_encountered += 1
            try:
                traceback_info = '\n'.join(traceback.format_exception(*(sys.exc_info())))
            except:
                traceback_info = ''
            print "*** ERROR PROCESSING: %s ***\nTraceback: %s\n" % ( current_url, traceback_info )
            
if __name__ == "__main__":
    output_dir = os.path.join( os.getcwd(), "output" )
    if not os.path.exists(output_dir):
        mkdir_p(output_dir)
    
    for d in urls_to_crawl:
        seed_url = d["url"]
        urls_to_visit = [seed_url]
        all_urls = [seed_url]
        follow_links_containing = d["follow_links_containing"]
        regex_filters = d.get("regex_filters")
        if regex_filters:
            using_regex_filters = True
            regex_filters = [ re.compile(regex_filter) for regex_filter in regex_filters ]
        else:
            using_regex_filters = False
        start_time = datetime.datetime.now()
        print start_time
        crawl_url()
        end_time = datetime.datetime.now()
        print "\nStart: %s\nFinish: %s" % (start_time, end_time)
