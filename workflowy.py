# From http://lukemerrett.com/workflowy-scheduling-in-python/ 
# Modified @Mon16oct2017, @Mon30oct2017
import time
#import date
#import settings
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.support.wait import WebDriverWait
 
 
class WorkflowyScheduler(object):
    workflowy_url = "https://workflowy.com"
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("window-size=1200,1100")
    #chrome_options.add_argument("remote-debugging-port=9222')
    #chrome_options.add_argument("disable-gpu")
    browser = webdriver.Chrome(executable_path="C:\python35\chromedriver-Windows", chrome_options=chrome_options)
    
    # Weekday abbreviations
    #weekdays = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
 
    @classmethod
    def execute_stuff(cls):
        #todays_date_tag = cls.__get_todays_date_tag()
        exec_tag = "#exec"
 
        cls.browser.get(cls.workflowy_url)
 
        cls.__login()
        cls.__search(exec_tag)
        #cls.__mark_results_with_tag("#Focus")
        cls.__save_changes()
 
        #cls.browser.close()

    @classmethod
    def get_reminders(cls):
        todays_date_tag = cls.__get_todays_date_tag()
        reminder_tag = "#remind" + " " + todays_date_tag
 
        cls.browser.get(cls.workflowy_url)
        
        print("Logging in.")
        cls.__login()
        print("Logged in.")
        cls.__search(reminder_tag)
        print("Searched.")
        results = cls.__get_results()
        cls.__mark_results_with_tag("#seen")
        cls.__save_changes()
 
        cls.browser.close()
        return results
 
    @classmethod
    def __login(cls):
        cls.__click_button("div.header-bar a.button--top-right")
        cls.__wait_for_element_to_appear("#id_username")
        cls.__fill_text_box("#id_username", "erickball@fastmail.com")
        cls.__fill_text_box("#id_password", "tSt.fic5")
        cls.__click_button("input.button--submit")
 
    @classmethod
    def __search(cls, search_term: str):
        cls.__wait_for_element_to_appear("#searchBox")
        print("Found search box.")
        cls.__fill_text_box("#searchBox", search_term)
        #print("Filled search box.")

    @classmethod
    def __execute_tagged(cls, tag: str):
        print(cls.browser.find_elements_by_css_selector("div.name.matches"))
        for element in cls.browser.find_elements_by_css_selector("div.name.matches"):
            text = element.text
            print(text)
            if "#=" not in text:
                text_box = element.find_element_by_css_selector("div.content")
                text_box.click()
                text_box.send_keys(Keys.SHIFT + Keys.RETURN)
                note_box = element.find_element_by_css_selector("div.content.focusedButWindowBlurred")
                note_box.send_keys(" #= " + "result")

    @classmethod
    def __mark_results_with_tag(cls, tag: str):
        for element in cls.browser.find_elements_by_css_selector("div.name.matches"):
            text = element.text
            if tag not in text:
                text_box = element.find_element_by_css_selector("div.content")
                text_box.click()
                text_box.send_keys(Keys.END) #Note: no good for multi-line items
                text_box.send_keys(" " + tag + " ")

    @classmethod
    def __get_results(cls):
        print("Results: ")
        num_results = len(cls.browser.find_elements_by_css_selector("div.name.matches"))
        result = "" #str(num_results) + "\n"
        print(str(len(cls.browser.find_elements_by_css_selector("div.name.matches"))) + "\n")
        for element in cls.browser.find_elements_by_css_selector("div.name.matches"):
            text = element.text
            print("\n" + text)
            result += "\n" + text
        return result
 
    @classmethod
    def __save_changes(cls):
        cls.browser.find_element_by_css_selector("div.saveButton").click()
        cls.__wait_for_element_to_appear("div.saveButton.saved")
 
    @classmethod
    def __click_button(cls, css_selector: str):
        cls.browser.find_element_by_css_selector(css_selector).click()
 
    @classmethod
    def __wait_for_element_to_appear(cls, css_selector):
        WebDriverWait(cls.browser, 15).until(
                lambda driver: driver.find_element_by_css_selector(css_selector))
 
    @classmethod
    def __fill_text_box(cls, css_selector: str, text_to_input: str):
        cls.browser.find_element_by_css_selector(css_selector).send_keys(text_to_input)
 
    @classmethod
    def __get_todays_date_tag(cls) -> str:
        #daynum = date.weekday()
        #day = cls.weekdays[daynum]
        
        return "@%s" % time.strftime("%a%d%b%Y")
 
 
if __name__ == "__main__":
    print("Starting.\n")
    WorkflowyScheduler.get_reminders()

