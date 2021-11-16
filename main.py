# -*- coding: utf-8 -*-
from login import U_NAME, PWD, TOKEN
from PIL import Image
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from Screenshot import Screenshot_Clipping
import telegram_send
from warnings import filterwarnings
import keyring,re,json,atexit,sys,difflib,io,telegram,time,telegram_send,time


#
# A script that scraps the moodle page for changes, sends a telegram message.
#

filterwarnings("ignore",category = DeprecationWarning)
sleep_time_min = 5  # the amount of minutes to sleep between checks

# A class of course page. Has a name, id, and the page html contents
class CoursePage:
    def __init__(self,name,page_id,html):
        self.name = name
        self.page_id = page_id
        self.html = html
# Go to the moodle homepage and login using the credentials in the keyring
def selenium_login(driver):
    driver.get('https://lemida.biu.ac.il/')
    search_box1 = driver.find_element_by_id("login_username")
    search_box2 = driver.find_element_by_id("login_password")
    submit_button = driver.find_element_by_xpath("//input[@type='submit' and @value='התחברות']")
    user_name = U_NAME  #ID goes here
    search_box1.send_keys(user_name)
    #search_box2.send_keys(keyring.get_password("moodle",user_name))  #Get the password from the keyring
    search_box2.send_keys(PWD)
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
    sys.stdout.close()

# function to save the data to a json file
def dump_json(course_list):
    with open('data.json','w+',encoding = 'utf-8') as f:
        print("Dumping data to json",flush = True)
        json.dump(course_list,f,ensure_ascii = False,indent = 4,default = obj_dict)
        f.close()

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
    driver.get("https://lemida.biu.ac.il/course/view.php?id=" + page["page_id"])
    temp_html = driver.find_element_by_id("region-main").get_attribute("innerHTML")
    soup = BeautifulSoup(temp_html,"lxml")
    formatted_html = soup.get_text("\n",strip = False)
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

#CHROME_PATH = '/usr/lib/chromium-browser/chromium-browser-v7'  #path to chrome app
CHROMEDRIVER_PATH = '/usr/lib/chromium-browser/chromedriver'  #path to chrome driver
WINDOW_SIZE = "1920,1080"
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
#chrome_options.binary_location = CHROME_PATH
chrome_options.add_argument("--log-level=3")  #disable logging into the console
chrome_options.add_experimental_option('excludeSwitches',['enable-logging'])
driver = webdriver.Chrome(executable_path = CHROMEDRIVER_PATH,options = chrome_options)  # generate the driver
atexit.register(exit_handler)  # when the script exits run function exit_handler
ob = Screenshot_Clipping.Screenshot()
bot = telegram.Bot(token = TOKEN)
my_chat_id = '715815893'
group_chat_id = '-1001625759648'
print("Trying to load file...",flush = True)
# try to load data from a json file
try:
    f = open('data.json',mode = 'r',encoding = "utf-8")
    # populate the course list with data from json
    course_list = json.load(f)
    f.close()
    print("json loaded",flush = True)
# if the file wasn't loaded properly we need to get the information via Selenium again
except:
    print("json not found, getting list via Selenium",flush = True)
    selenium_login(driver)  #login webdriver to moodle
    #driver = webdriver.Chrome(executable_path = CHROMEDRIVER_PATH,options = chrome_options)
    #driver.get_screenshot_as_file("capture" + ".png")  # take screenshot
    pages_id_list = ["67199","66254","66219","66210","66244"]  # list of page ID's for the courses
    my_dict = {}
    html_list = []
    course_list = []
    #iterate through all the given page ID and map them to the course name
    for s in pages_id_list:
        driver.get("https://lemida.biu.ac.il/course/view.php?id=" + s)  #go to course page using id from list
        course_name = driver.find_element_by_xpath("//*[@id='sitetitle']/h1").get_attribute(
            "innerHTML")  # get  name from page
        temp_html = driver.find_element_by_id("region-main").get_attribute(
            "innerHTML")  # find the region with the course info
        soup = BeautifulSoup(temp_html,"lxml")  # parse the html using BS
        formatted_html = soup.get_text("\n",strip = False)  #get text from HTML using soup
        my_dict[s] = course_name  # map page id to course name
        course_list.append(CoursePage(course_name,s,formatted_html))  # create a new course object and add to the list
    print("Finished iterating through the pages",flush = True)
    # close the driver
    driver.close()
    driver.quit()
    # save the data we got to a json file
    dump_json(course_list)
    f = open('data.json',mode = 'r',encoding = "utf-8")
    course_list = json.load(f)
    # flush the buffer of the file (prevents cmd from getting stuck)
    f.flush()
    f.close()

try:
    # main loop of the script
    while True:
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        print(dt_string,flush = True)
        print("Preforming comparison",flush = True)
        # driver = webdriver.Chrome(executable_path = CHROMEDRIVER_PATH,options = chrome_options)
        # login to moodle if needed
        try:
            selenium_login(driver)
        except:
            pass
        # iterate through all the courses we have in the list
        for page in course_list:
            # go to the course page
            # driver.get("https://lemida.biu.ac.il/course/view.php?id=" + page["page_id"])
            # temp_html = driver.find_element_by_id("region-main").get_attribute("innerHTML")
            # soup = BeautifulSoup(temp_html,"lxml")
            # formatted_html = soup.get_text("\n",strip = False)
            formatted_html = get_formatted_html(page)
            # if the page has an error, wait a minute and retry
            if "Error" in formatted_html or "טעות שגיאה" in formatted_html:
                time.sleep(60)
                # driver.get("https://lemida.biu.ac.il/course/view.php?id=" + page["page_id"])
                # temp_html = driver.find_element_by_id("region-main").get_attribute("innerHTML")
                # soup = BeautifulSoup(temp_html,"lxml")
                # formatted_html = soup.get_text("\n",strip = False)
                formatted_html = get_formatted_html(page)
            # if the formatted html is the same as new HTML
            if formatted_html == page["html"]:
                # reverse a name to print it out mirrored to the cmd
                page_name_reverse = ((page["name"])[::-1]).encode('utf8')
                print("No differences found in " + page_name_reverse.decode('utf8'),flush = True)
                driver.get_screenshot_as_file("capture" + page["name"] + ".png")  #take screenshot
                continue
            else:
                # reverse a name to print it out mirrored to the cmd
                page_name_reverse = ((page["name"])[::-1]).encode('utf8')
                print("HTML's differ in " + page_name_reverse.decode('utf8'),flush = True)
                now = datetime.now()
                dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
                #diff_str = str((formatted_html.split(page["html"]))[0])
                # get the difference between the pages in a string
                diff_str = compare_html_strings(page["html"],formatted_html)
                # write the changes to a text file
                with open(file = "out.txt",mode = "a",encoding = 'utf8') as f:
                    f.write(dt_string + "\n" + page["name"] + ": \n")
                    # f.write("Old:\n" + page['html'] + "\n################\n") #DEBUG
                    # f.write("New:\n" + formatted_html + "\n################\n") #DEBUG
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
                    #telegram_send.send(messages = ["Difference found in page " + page["name"]])
                    bot.send_message(text = "עמוד הקורס " + page["name"] + " עודכן,התוספת היא: \n" + diff_str,
                                     chat_id = group_chat_id)
                # if there is an exercise and not a solution to an exercise
                elif (re.search(pattern,diff_str) or re.search(other_pattern,diff_str)) and not re.search('פתרון',
                                                                                                        diff_str):
                    #telegram_send.send(messages = ["Difference contains exercise: \n",diff_str])
                    #telegram_send.send(messages = ["עמוד הקורס עודכן,התוספת היא: \n" + diff_str])
                    bot.send_message(text = "עמוד הקורס " + page[
                        "name"] + " עודכן והעדכון מכיל את המילה תרגיל,התוספת היא: \n" + diff_str,chat_id = group_chat_id)
                driver.get_screenshot_as_file("capture" + page["name"] + ".png")  #take screenshot
                screenshot_name = ("capture" + page["name"] + ".png")
                img_url = ob.full_Screenshot(driver, save_path=r'.', image_name="FULL " + page["name"] + ".png")
                send_photo_PIL(img_url)
                # save the new html to the course object
                page["html"] = formatted_html
                # save the new data to the json file
                dump_json(course_list)
                f = open('data.json',mode = 'r',encoding = "utf-8")
                course_list = json.load(f)
                f.flush()
                f.close()
        # driver.close()
        # driver.quit()
        print("Waiting " + str(sleep_time_min) + " minutes",flush = True)
        sys.stdout.flush()
        # sleep for the required number of minutes
        time.sleep(60 * sleep_time_min)
except KeyboardInterrupt as e:
    exit_handler()
    exit()
