# -*- coding: utf-8 -*-
from asyncio import sleep
from multiprocessing.connection import wait
from tkinter.tix import Tree
from login import U_NAME, PWD, TOKEN # the credentials are saved in a different file for security
from PIL import Image
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from Screenshot import Screenshot_Clipping
from warnings import filterwarnings
import re,json,atexit,sys,difflib,io,telegram,time,telegram_send,time
import requests


#
# A script that scraps the moodle page for changes, sends a telegram message.
#

filterwarnings("ignore",category = DeprecationWarning)
sleep_time_min = 5  # the amount of minutes to sleep between checks
restarted_flag = False # flag to see if the script restarted or first started
launched = False
# A class of course page. Has a name, id, and the page html contents
class CoursePage:
    def __init__(self,name,page_id,html):
        self.name = name
        self.page_id = page_id
        self.html = html
# Go to the moodle homepage and login using the credentials in the keyring
def selenium_login(driver):
    driver.get('https://lemida.biu.ac.il/')
    try:
        driver.find_element_by_id("usermenu")
        return
    except Exception as e1:
        print("usermenu not found,continuing login")
    search_box1 = driver.find_element_by_id("login_username")
    search_box2 = driver.find_element_by_id("login_password")
    submit_button = driver.find_element_by_xpath("//input[@type='submit' and @value='התחברות']")
    user_name = U_NAME  #ID goes here
    search_box1.send_keys(user_name)
    search_box2.send_keys(PWD) #password goes here
    submit_button.click()  #log in
    time.sleep(2)

def obj_dict(obj):
    return obj.__dict__

# function for handling the exit
def exit_handler():
    # try to close the driver
    try:
        driver.close()
        driver.quit()
    # if the driver iss already closed
    except:
        print("Exiting..",flush = True)
    if(launched):
        bot.send_message(text = "Script exited",
                                     chat_id = my_chat_id)
    sys.stdout.close()

# function to save the data to a json file
def dump_json(course_list):
    with open('data.json' ,'w',encoding = 'utf-8') as f:
        print("Dumping data to json",flush = True)
        json.dump(course_list,f,ensure_ascii = False,indent = 4,default = obj_dict)
        f.flush()
        f.close()
        print("Finished dumping json")

# convert a dictionary to a page object
def dict_to_course(page):
    if type(page) is CoursePage:
        return page
    return (CoursePage(page["name"],page["page_id"],page["html"]))

# get two strings and compare them using difflib.
def compare_html_strings(a,b):
    # split the strings into lists of words
    list_a = a.split()
    list_b = b.split()
    d = difflib.Differ()
    diff = d.compare(list_a,list_b)
    new_str = []  # empty list for the string
    # iterate through the list of differences, and add all the words present in b and not in a to the list
    for s in list(diff):
        if '+' in s and '?' not in s:
            new_str.append(s.replace('+',''))  #print(s.replace('+',''))
    # join the list into a string
    return " ".join(new_str)

def get_formatted_html(page):
    formatted_html = None
    try:
        # if type(page) is CoursePage:
        driver.get("https://lemida.biu.ac.il/course/view.php?id=" + page.page_id)
        # if type(page) is dict:
        #     driver.get("https://lemida.biu.ac.il/course/view.php?id=" + page["page_id"])
        temp_html = driver.find_element_by_id("region-main").get_attribute("innerHTML")
        soup = BeautifulSoup(temp_html,"lxml")
        formatted_html = soup.get_text("\n",strip = False)
    except requests.exceptions.ConnectionError:
        print("Connection refused,sleeping for five") 
        time.sleep(5)
    except Exception as e:
        print(e)
    return formatted_html

def send_photo_PIL(fp):
    #open image
    im = Image.open(fp)
    # get bytes for a buffer from system
    buf = io.BytesIO()
    #save the image to buffer
    im.save(buf,format = 'PNG')
    byte_im = buf.getvalue()
    bot.send_document(document = byte_im,chat_id = my_chat_id,filename = fp)

# function to check  if  we are in a certain timerange
def check_timerange():
    now = datetime.datetime.now()
    # check the timerange between midnight and 5 in the morning
    start = datetime.time(hour = 00, minute = 1)
    end = datetime.time(5)
    return (start <= now.time() <= end)

# make a course page object from a passed id
def course_page_from_id(course_id):
            driver.get("https://lemida.biu.ac.il/course/view.php?id=" + course_id)  #go to course page using id from list
            course_name = driver.find_element_by_xpath("//*[@id='sitetitle']/h1").get_attribute(
                "innerHTML")  # get  name from page
            temp_html = driver.find_element_by_id("region-main").get_attribute(
                "innerHTML")  # find the region with the course info
            soup = BeautifulSoup(temp_html,"lxml")  # parse the html using BS
            formatted_html = soup.get_text("\n",strip = False)  #get text from HTML using soup
            
            return (CoursePage(course_name,course_id,formatted_html))  # create a new course object and return it


# main loop of the code - goes over the passed list, checking whether the pages in the page id are all present.
# checks if the html saved in the object in the list is the same as the html we scrape from the page
# notifies about the changes using telegram
def main_loop(course_list):
    global pages_id_list #the list that hold the id of courses for navigating to their web page
    try:
        # main loop of the script
        while True:
            # print out the timestamp with visual separator
            now = datetime.datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
            print("#####################################")
            print(dt_string,flush = True)
            print("Preforming comparison",flush = True)
            
            
            # iterate through all the courses we have in the list
            for s in pages_id_list:
                # login to moodle if needed
                try:
                    selenium_login(driver)
                except:
                    print("Got exception when trying to login.")
                
                page = next((x for x in course_list if x.page_id == s), None)
                # if no entry with page_id==s is found in the course list,
                if page == None:
                    page = course_page_from_id(s)
                    course_list.append(page)
                    formatted_html = page.html
                else:
                    formatted_html = get_formatted_html(page)
                # if the page has an error, wait a minute and retry
                pattern1 = re.compile('(((E|e)rror)+)|(טעות)|(שגיאה)')
                pattern_lock = re.compile('((s|S)ession lock)')
                pattern_guest = re.compile('((אורחים  אינם )|(אפשרויות  גישה))')
                if (pattern_lock.findall(formatted_html)):
                    print("Session lock issue, sleeping for "+str(sleep_time_min)+" minutes")
                    sleep(60*sleep_time_min)
                    break
                while (pattern1.findall(formatted_html)):
                    print("Error in moodle page, sleeping")
                    img_url = ob.full_Screenshot(driver,save_path = r'.',image_name = "FULL " + page.name + ".png")
                    send_photo_PIL(img_url)
                    time.sleep(120)
                    formatted_html = get_formatted_html(page)
                # if we need to login
                while "אורחים" in formatted_html or "זיהוי" in formatted_html or pattern_guest.findall(formatted_html):
                    print("Logged out, preforming login")
                    selenium_login(driver)
                    time.sleep(1)
                    formatted_html = get_formatted_html(page)

                # get the difference between the pages in a string
                diff_str = compare_html_strings(page.html,formatted_html)
                # no difference in the page html
                if formatted_html == page.html or diff_str=='':
                    # reverse a name to print it out mirrored to the cmd
                    page_name_reverse = ((page.name)).encode('utf8')
                    print("No differences found in " + page_name_reverse.decode('utf8'),flush = True)
                    driver.get_screenshot_as_file("capture" + page.name + ".png")  #take screenshot
                    continue
                else:
                    # reverse a name to print it out mirrored to the cmd
                    page_name_reverse = ((page.name)[::-1]).encode('utf8')
                    print("HTML's differ in " + page_name_reverse.decode('utf8'),flush = True)
                    now = datetime.datetime.now()
                    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
                    # write the changes to a text file
                    with open(file = "out.txt",mode = "a",encoding = 'utf8') as f:
                        f.write(dt_string + "\n" + page.name + ": \n")
                        f.write(diff_str)
                        f.write("\n********************************************************\n")
                        f.flush()
                        f.close()
                    print("*****************************",flush = True)
                    pattern = 'תרגיל'  #pattern for regex
                    pattern2 = 'משוב'  #pattern for regex
                    pattern3 = 'הוגש  בתאריך'
                    other_pattern = '(EX | ex)'
                    if not re.search(pattern2,diff_str) and not re.search(pattern3,diff_str):
                        #telegram_send.send(messages = ["Difference found in page " + page.name])
                        try:
                            bot.send_message(text = "עמוד הקורס " + page.name + " עודכן,התוספת היא: \n" + diff_str,
                                            chat_id = group_chat_id)
                        except:
                            bot.send_message(text = "Update message threw an exception",
                                            chat_id = my_chat_id)
                            pass
                    # if there is an exercise and not a solution to an exercise
                    elif (re.search(pattern,diff_str) or re.search(other_pattern,diff_str)) and not re.search('פתרון',
                                                                                                            diff_str):
                        try:
                            bot.send_message(text = "עמוד הקורס " + page.name + " עודכן והעדכון מכיל את המילה תרגיל,התוספת היא: \n" + diff_str,
                                            chat_id = group_chat_id)
                        except:
                            bot.send_message(text = "Update message threw an exception",
                                            chat_id = my_chat_id)
                            pass
                    driver.get_screenshot_as_file("capture" + page.name + ".png")  #take screenshot
                    img_url = ob.full_Screenshot(driver,save_path = r'.',image_name = "FULL " + page.name + ".png")
                    send_photo_PIL(img_url)
                    # save the new html to the course object
                    page.html = formatted_html
            
            # save the new data to the json file
            dump_json(course_list)
            sys.stdout.flush()

            # sleep for the required number of minutes
            # check if it's night time and sleep for longer
            print("Iteration complete,sleeping")
            if check_timerange():
                time.sleep(60 * 40)
            else:
                time.sleep(60 * sleep_time_min)
    except Exception as e:
        print(e)

# a wrapper function for the main_loop
# loads the json file containing the data, and if needed fetches it from the webpages
def main():
    global retries
    print("Starting main function")
    global pages_id_list
    pages_id_list = ["69089","70232","69037","69059","69061","69278"]  # list of page ID's for the courses
    global restarted_flag
    # differentiate between a start of the script and restart
    if not restarted_flag:
        bot.send_message(text = "Script started",chat_id = my_chat_id)
        restarted_flag = True
    else:
        # flood control
        if retries>5:
            exit(-1)
        retries+=1
        bot.send_message(text = "Script RESTARTED",chat_id = my_chat_id)
        
    print("Trying to load file...",flush = True)
    # try to load data from a json file
    course_list = []
    try:
        f = open('data.json',mode = 'r',encoding = "utf-8")
        # populate the course list with data from json
        course_list_dict = json.load(f)
        f.close()
        # the json returns a disctionary, transform to list of course page objects
        for c in course_list_dict:
            course_list.append(dict_to_course(course_list_dict.pop(course_list_dict.index(c))))
        print("json loaded",flush = True)
    # if the file wasn't loaded properly we need to get the information via Selenium again
    except:
        print("json not found, getting list via Selenium",flush = True)
        try:
            selenium_login(driver)  #login webdriver to moodle
        except:
            print("Got an exception during login in main.")

        my_dict = {}
        #iterate through all the given page ID and map them to the course name
        for s in pages_id_list:
            temp_course = course_page_from_id(s)
            course_list.append(temp_course)
            # create a new course object and add to the list
            my_dict[s] = temp_course.name  # map page id to course name
        print("Finished iterating through the pages",flush = True)

        # save the data we got to a json file
        dump_json(course_list)
        f = open('data.json',mode = 'r',encoding = "utf-8")
        #get the courses as dictionary (default json format) and add them to a list as course objects
        course_list_dict = json.load(f)
        for c in course_list_dict:
            course_list.append(dict_to_course(course_list_dict.pop(course_list_dict.index(c))))

        # flush the buffer of the file (prevents terminal from getting stuck)
        f.flush()
        f.close()
        time.sleep(60 * sleep_time_min)
    # finished building the data, run the main loop
    main_loop(course_list)

bot = telegram.Bot(token = TOKEN)
my_chat_id = '715815893'
group_chat_id = '-1001625759648'
atexit.register(exit_handler)
CHROME_PATH = '/usr/lib/chromium-browser/chromium-browser'  #path to chrome app
CHROMEDRIVER_PATH = '/usr/bin/chromedriver'  #path to chrome driver
WINDOW_SIZE = "1920,1080"
chrome_options = Options()
#chrome_options.binary_location = CHROME_PATH
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
chrome_options.add_argument('--no-sandbox')        
chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; CrOS armv7l 13597.84.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.106 Safari/537.36')
try:
    driver = webdriver.Chrome(options = chrome_options)  # generate the driver.
    launched = True
except:
    print("Failed to generate driver")
driver.implicitly_wait(5)
ob = Screenshot_Clipping.Screenshot()


if __name__ == "__main__":
    retries = 0
    print("Launching bot..")
    while True:
        try:
            main()
        except KeyboardInterrupt as k:
            exit()
        except Exception as e:
            print(e)
            