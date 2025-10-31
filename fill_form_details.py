from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
import time

def format_phone_number(phone_str):
    return ''.join(filter(str.isdigit, phone_str))


def simple_form_details(driver, user_data):
    # Define the fields
    fields = {
        'first_name': {
            'xpath': '//*[@id="formly_33_input_firstName_1"]',
            'value': user_data['first_name'],
        },
        'last_name': {
            'xpath': '//*[@id="formly_33_input_surname_2"]',
            'value': user_data['last_name'],
        },
        'contact': {
            'xpath': '//*[@id="formly_33_input_mobileNumber_3"]',
            'value': user_data['contact'],
        },
        'email': {
            'xpath': '//*[@id="formly_33_input_email_5"]',
            'value': user_data['email']
        }
    }

    # Define repair types
    repair_type_xpath = {
        'Home': '//*[@id="formly_66_radio_homeCommon_1_0"]',
        'Common': '//*[@id="formly_66_radio_homeCommon_1_1"]'
    }

    # Fill in the fields
    for field in fields.values():
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, field['xpath']))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        element.send_keys(field['value'])

    # Wait for page to load completely
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'p-autocomplete input.p-autocomplete-input'))
    )

    # Locate the address input field using the CSS Selector
    address_input = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'p-autocomplete input.p-autocomplete-input'))
    )

    # Scroll to the email field
    email_field = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="formly_33_input_email_5"]'))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", email_field)
    time.sleep(1)

    # Input partial address to trigger autocomplete
    address_input.clear()
    address_input.send_keys(user_data['address'])

    # Wait for autocomplete dropdown and select first option
    try:
        dropdown = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'ul.p-autocomplete-items'))
        )
        first_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'ul.p-autocomplete-items li'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", first_option)
        first_option.click()
    except TimeoutException:
        print("Dropdown menu did not appear or there was an issue selecting the first item.")

    time.sleep(1)

    # Scroll to repair type section and select the appropriate repair type
    repair_type_checkbox = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, repair_type_xpath[user_data['repair_type']]))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", repair_type_checkbox)
    time.sleep(1)

    # Attempt to click the repair type checkbox and handle click interception
    try:
        repair_type_checkbox.click()
    except ElementClickInterceptedException:
        print("Click intercepted! Trying to click using JavaScript...")
        driver.execute_script("arguments[0].click();", repair_type_checkbox)

    time.sleep(1)
    
    
def common_form_details(driver, user_data):
    # Select Issue Location Dropdown
    dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_commonRepairLocation_7']//div[@role='button']"
    dropdown_trigger = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", dropdown_trigger)
    time.sleep(2)
    dropdown_trigger.click()
    time.sleep(2)
    issue_location_option_xpath = f"//p-dropdown[@id='formly_66_select_commonRepairLocation_7']//p-overlay//span[contains(text(), '{user_data['issue_location']}')]"
    issue_location_option = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, issue_location_option_xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", issue_location_option)
    issue_location_option.click()
    time.sleep(1)
    # Select Issue Area Dropdown
    dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_commonRepairArea_9']//div[@role='button']"
    dropdown_trigger = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
    )
    dropdown_trigger.click()
    time.sleep(1)
    issue_area_option_xpath = f"//p-dropdown[@id='formly_66_select_commonRepairArea_9']//p-overlay//span[contains(text(), '{user_data['issue_area']}')]"
    issue_area_option = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, issue_area_option_xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", issue_area_option)
    issue_area_option.click()
    time.sleep(1)
    

    checkbox_xpath_1 = "//input[@id='formly_66_multicheckbox_commonIssueRaisedInTheLastSixMonths_14_0']"

    # Check if we should click the checkboxes based on issue_raised
    if user_data['issue_raised'] != 'No':
        try:
            checkbox = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, checkbox_xpath_1))
            )
            driver.execute_script("arguments[0].click();", checkbox)
            print(f"Checkbox with XPath '{checkbox_xpath_1}' clicked.")
        except:
            print(f"Checkbox with XPath '{checkbox_xpath_1}' not found.")
    else:
        print("Issue raised is 'No'; skipping checkbox clicks.")

    time.sleep(1)
    
    # Select Issue Type Dropdown
    dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_commonRepairIssueRelateTo_10']//div[@role='button']"
    dropdown_trigger = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
    )
    dropdown_trigger.click()
    time.sleep(1)
    issue_type_option_xpath = f"//p-dropdown[@id='formly_66_select_commonRepairIssueRelateTo_10']//p-overlay//span[contains(text(), '{user_data['issue_type']}')]"
    issue_type_option = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, issue_type_option_xpath))
    )
    issue_type_option.click()
    time.sleep(1)
    # Select Issue Detail Dropdown
    
    if user_data["issue_location"] == "Inside":
        dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_commonRepairFloor_8']//div[@role='button']"
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
        )

        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", dropdown_trigger)
        dropdown_trigger.click()        
        time.sleep(1)
        issue_detail_option_xpath = f"//p-dropdown[@id='formly_66_select_commonRepairFloor_8']//p-overlay//span[contains(text(), '{user_data['common_inside_floor']}')]"
        issue_detail_option = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, issue_detail_option_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", issue_detail_option)
        issue_detail_option.click()
        
        time.sleep(1)
        
        dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_commonInsideRepairIssue_11']//div[@role='button']"
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", dropdown_trigger)
        dropdown_trigger.click()
        time.sleep(1)
        issue_detail_option_xpath = f"//p-dropdown[@id='formly_66_select_commonInsideRepairIssue_11']//p-overlay//span[contains(text(), '{user_data['issue_detail']}')]"
        issue_detail_option = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, issue_detail_option_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", issue_detail_option)
        issue_detail_option.click()
    elif user_data["issue_location"] == "Outside":
        dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_commonOutsideRepairIssue_12']//div[@role='button']"
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", dropdown_trigger)
        dropdown_trigger.click()
        time.sleep(1)
        issue_detail_option_xpath = f"//p-dropdown[@id='formly_66_select_commonOutsideRepairIssue_12']//p-overlay//span[contains(text(), '{user_data['issue_detail']}')]"
        issue_detail_option = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, issue_detail_option_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", issue_detail_option)
        issue_detail_option.click()

    # Enter Common Area in the Textarea
    textarea_xpath = "//textarea[@id='formly_66_textarea_commonRepairLocateArea_16']"
    textarea = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, textarea_xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", textarea)
    time.sleep(1)  # Optional delay for smooth interaction
    textarea.clear()  # Clear any pre-existing text

    common_area_str = f"{user_data['common_area']}"
    textarea.send_keys(common_area_str)
    time.sleep(1)
    # Click the "OK" button
    ok_button_xpath = "//button[@class='p-ripple p-element p-button-conversion p-button p-component']//span[text()='OK']"
    try:
        ok_button = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, ok_button_xpath))
        )
        ok_button.click()
        print("OK button clicked")
    except TimeoutException:
        print("OK button not found or not clickable")

    time.sleep(1)
    # Enter Issue Text in the Textarea
    textarea_xpath = "//textarea[@id='formly_66_textarea_commonTellUsMore_20']"
    textarea = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, textarea_xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", textarea)
    time.sleep(1)  # Optional delay for smooth interaction
    textarea.clear()  # Clear any pre-existing text

    issue_text_str = f"{user_data['issue_detail']}. {user_data['issue_text']}"
    textarea.send_keys(issue_text_str)

    time.sleep(1)

    submit_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "page1-btnSubmit"))
    )

    # Scroll the button into view
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_button)

    # Pause to ensure the scroll has completed
    time.sleep(1)

    # Click the button using JavaScript
    # driver.execute_script("arguments[0].click();", submit_button)
    driver.execute_script("arguments[0].remove();", submit_button)
    

    # yes_button_xpath = "//button[contains(@class, 'p-confirm-dialog-accept') and .//span[text()='Yes']]"
    # yes_button = WebDriverWait(driver, 10).until(
    #     EC.element_to_be_clickable((By.XPATH, yes_button_xpath))
    # )

    # Click the "Yes" button using JavaScript
    # driver.execute_script("arguments[0].click();", yes_button)
    # Click the OK Button
    # ok_button_xpath = "//button[@class='p-ripple p-element p-button-conversion p-button p-component']//span[text()='OK']"
    # ok_button = WebDriverWait(driver, 10).until(
    #     EC.element_to_be_clickable((By.XPATH, ok_button_xpath))
    # )
    # ok_button.click()

def home_form_details(driver, user_data):
    # Function to handle dropdown selection
    def select_dropdown_option(dropdown_xpath, option_xpath):
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, dropdown_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", dropdown_trigger)
        time.sleep(2)  # Optional delay for smooth interaction
        dropdown_trigger.click()

        option = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, option_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", option)
        time.sleep(1)  # Optional delay
        option.click()

    # Issue Location Dropdown
    select_dropdown_option(
        "//p-dropdown[@id='formly_66_select_homeRepairLocation_2']//div[@role='button']",
        f"//p-dropdown[@id='formly_66_select_homeRepairLocation_2']//p-overlay//span[contains(text(), '{user_data['issue_location']}')]"
    )

    # Issue Area Dropdown
    select_dropdown_option(
        "//p-dropdown[@id='formly_66_select_homeRepairRoomArea_3']//div[@role='button']",
        f"//p-dropdown[@id='formly_66_select_homeRepairRoomArea_3']//p-overlay//span[contains(text(), '{user_data['issue_area']}')]"
    )
    
    checkbox_xpath_1 = "//input[@id='formly_66_multicheckbox_issueRaisedInTheLastSixMonths_13_0']"

    # Check if we should click the checkboxes based on issue_raised
    if user_data['issue_raised'] != 'No':
        try:
            checkbox = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, checkbox_xpath_1))
            )
            driver.execute_script("arguments[0].click();", checkbox)
            print(f"Checkbox with XPath '{checkbox_xpath_1}' clicked.")
        except:
            print(f"Checkbox with XPath '{checkbox_xpath_1}' not found.")
    else:
        print("Issue raised is 'No'; skipping checkbox clicks.")

    time.sleep(2)

    # Issue Type Dropdown
    select_dropdown_option(
        "//p-dropdown[@id='formly_66_select_homeRepairIssueRelateTo_4']//div[@role='button']",
        f"//p-dropdown[@id='formly_66_select_homeRepairIssueRelateTo_4']//p-overlay//span[contains(text(), '{user_data['issue_type']}')]"
    )

    # Issue Details Dropdown
    if user_data['issue_location'] == 'Inside':
        issue_detail_xpath_inside =  f"//p-dropdown[@id='formly_66_select_homeInsideRepairIssue_5']//p-overlay//span[contains(text(), \"{user_data['issue_detail']}\")]"
        select_dropdown_option(
            "//p-dropdown[@id='formly_66_select_homeInsideRepairIssue_5']//div[@role='button']",
            issue_detail_xpath_inside
        )
    else:
        issue_detail_xpath_outside =  f"//p-dropdown[@id='formly_66_select_homeOutsideRepairIssue_6']//p-overlay//span[contains(text(), \"{user_data['issue_detail']}\")]"
        select_dropdown_option(
            "//p-dropdown[@id='formly_66_select_homeOutsideRepairIssue_6']//div[@role='button']",
            issue_detail_xpath_outside
        )

    time.sleep(2)
    ## Click the "OK" button
    ok_button_xpath = "//button[@class='p-ripple p-element p-button-conversion p-button p-component']//span[text()='OK']"
    try:
        ok_button = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, ok_button_xpath))
        )
        ok_button.click()
        print("OK button clicked")
    except TimeoutException:
        print("OK button not found or not clickable")

    time.sleep(2)
    # Text Input for "Tell Us More"
    textarea_xpath = "//textarea[@id='formly_66_textarea_tellUsMore_18']"
    textarea = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, textarea_xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", textarea)
    time.sleep(1)
    textarea.clear()
    issue_text_str = user_data['issue_text']
    textarea.send_keys(issue_text_str)

    time.sleep(1)

    submit_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "page1-btnSubmit"))
    )

    # Scroll the button into view
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_button)

    # Pause to ensure the scroll has completed
    time.sleep(1)

    # Click the button using JavaScript
    # driver.execute_script("arguments[0].click();", submit_button)
    driver.execute_script("arguments[0].remove();", submit_button)
    
