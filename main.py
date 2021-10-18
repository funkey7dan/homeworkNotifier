import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import telegram_send
from warnings import filterwarnings
import keyring
import json
import atexit

filterwarnings("ignore",category = DeprecationWarning)
sleep_time_min = 0.5
# A class of course page. Has a name, id, and the page html
class CoursePage:
    def __init__(self,name,page_id,html):
        self.name = name
        self.page_id = page_id
        self.html = html

def selenium_login():
    driver.get('https://lemida.biu.ac.il/')
    search_box1 = driver.find_element_by_id("login_username")
    search_box2 = driver.find_element_by_id("login_password")
    submit_button = driver.find_element_by_xpath("//input[@type='submit' and @value='התחברות']")
    user_name = "315901173"
    search_box1.send_keys(user_name)
    search_box2.send_keys(keyring.get_password("moodle",user_name))
    submit_button.click()
    time.sleep(2)

def obj_dict(obj):
    return obj.__dict__

def exit_handler():
    print("Exiting..")
    driver.close()
    driver.quit()

CHROME_PATH = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'  #path to chrome app
CHROMEDRIVER_PATH = 'C:/Users/funke/PycharmProjects/homeworkNotifier/chromedriver.exe'  #path to chrome driver
WINDOW_SIZE = "3440,1440"
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
chrome_options.binary_location = CHROME_PATH
atexit.register(exit_handler)
print("Trying to load file...")
try:
    f = open('data.json',mode = 'r',encoding = "utf-8")
    course_list = json.load(f)
    f.close()
    print("json loaded")
except:
    print("json not found, getting list via Selenium")
    selenium_login()
    driver = webdriver.Chrome(executable_path = CHROMEDRIVER_PATH,options = chrome_options)
    driver.get_screenshot_as_file("capture" + ".png")  # take screenshot
    pages_id_list = ["67199","66254","66219","66214","66244"]  # list of page ID's for the courses
    my_dict = {}
    html_list = []
    course_list = []
    #iterate through all the given page ID and map them to the course name
    for s in pages_id_list:
        driver.get("https://lemida.biu.ac.il/course/view.php?id=" + s)  #go to course page using id from list
        course_name = driver.find_element_by_xpath("//*[@id='sitetitle']/h1").get_attribute(
            "innerHTML")  # get  name from page
        temp_html = driver.find_element_by_id("region-main").get_attribute("innerHTML")
        soup = BeautifulSoup(temp_html,"lxml")
        formatted_html = soup.get_text("\n",strip = False)  #get text from HTML using soup
        my_dict[s] = course_name  # map page id to course name
        course_list.append(CoursePage(course_name,s,formatted_html))
    print("Finished iterating through the pages")
    driver.close()
    driver.quit()
    with open('data.json','w',encoding = 'utf-8') as f:
        print("Dumping data to json")
        json.dump(course_list,f,ensure_ascii = False,indent = 4,default = obj_dict)
        f.close()
    f = open('data.json',mode = 'r',encoding = "utf-8")
    course_list = json.load(f)
    f.close()

while True:
    print("Waiting " + str(sleep_time_min) + " minutes")
    time.sleep(60 * sleep_time_min)
    print("Preforming comparison")
    driver = webdriver.Chrome(executable_path = CHROMEDRIVER_PATH,options = chrome_options)
    selenium_login()
    for page in course_list:
        driver.get("https://lemida.biu.ac.il/course/view.php?id=" + page["page_id"])
        temp_html = driver.find_element_by_id("region-main").get_attribute("innerHTML")
        soup = BeautifulSoup(temp_html,"lxml")
        formatted_html = soup.get_text("\n",strip = False)
        if formatted_html == page["html"]:
            print("No differences found in" + page["name"])
            continue
        else:
            print("HTML's differ:")
            print(page.html.split(formatted_html))
            print("*****************************")
            telegram_send.send(messages = ["Difference found in page " + page.name])
            driver.get_screenshot_as_file("capture" + page.name + ".png")  #take screenshot
        driver.quit()
        driver.close()
