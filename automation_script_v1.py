import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException

import re

def extract_user_data_from_log(file_path):
    # Initialize the dictionary to store the parsed data
    user_data = {
        "first_name": None,
        "last_name": None,
        "contact": None,
        "email": None,
        "address": None,
        "repair_type": None,  # Field for repair type (Home or Common)
        "issue_location": None,  # Field for issue location (Inside or Outside)
        "issue_area": None,
        "issue_type": None,  # General type of issue, e.g., Electrical
        "issue_detail_option": "Other",  # Always set to "Other"
        "issue_raised": "Yes",
        "issue_text": None  # Detailed issue description
    }

    current_author = None
    current_question = None
    issue_text_captured = False  # To track when issue_text has been captured
    
    # Open the log file and read it line by line
    with open(file_path, 'r') as file:
        data = file.readlines()

    # Iterate through the lines to extract user answers
    for i, line in enumerate(data):
        line = line.strip().rstrip(',')

        # Detect who is speaking (either ChatGPT or User)
        if '"Author": "ChatGPT"' in line:
            current_author = "ChatGPT"
        elif '"Author": "User"' in line:
            current_author = "User"

        # Capture the Text response from User
        if current_author == "User" and '"Text":' in line:
            user_response = re.search(r'"Text": "(.*)"', line)
            if user_response:
                response = user_response.group(1).strip()

                # Ignore confirmation responses like "Yes", "Yes." or "No, that's all."
                if response.lower() in ["yes", "yes.", "no, that's all."]:
                    continue

                # Assign responses based on the last known question
                if current_question == "first_name":
                    user_data["first_name"] = response
                elif current_question == "last_name":
                    user_data["last_name"] = response.rstrip('.')
                elif current_question == "contact":
                    user_data["contact"] = format_phone_number(response)
                elif current_question == "email":
                    user_data["email"] = response
                elif current_question == "address":
                    user_data["address"] = response
                elif current_question == "repair_type":
                    user_data["repair_type"] = "Home" if "Home" in response else "Common"
                elif current_question == "issue_location":
                    user_data["issue_location"] = "Inside" if "Inside" in response else "Outside"
                elif current_question == "issue_area":
                    user_data["issue_area"] = response
                elif current_question == "issue_type":
                    user_data["issue_type"] = response  # The general type of issue (e.g., Electrical)
                elif current_question == "issue_text" and not issue_text_captured:
                    user_data["issue_text"] = response  # The detailed description of the issue
                    issue_text_captured = True  # Mark issue_text as captured

        # Capture the question from ChatGPT to set the current question
        if current_author == "ChatGPT" and '"Text":' in line:
            if "first name" in line:
                current_question = "first_name"
            elif "last name" in line:
                current_question = "last_name"
            elif "phone number" in line:
                current_question = "contact"
            elif "email address" in line:
                current_question = "email"
            elif "address of the property" in line:
                current_question = "address"
            elif "repair needed" in line:
                current_question = "repair_type"
            elif "inside or outside" in line:
                current_question = "issue_location"
            elif "area the issue is in" in line:
                current_question = "issue_area"
            elif "issue related to" in line:
                current_question = "issue_type"  # General issue type
            elif "describe the electrical issue" in line or "provide more details" in line:
                current_question = "issue_text"  # Detailed issue description
    
    return user_data

def format_phone_number(phone_str):
    # Remove any non-numeric characters
    return ''.join(filter(str.isdigit, phone_str))


# File path of the input log file
file_path = 'log-sample.txt'

# Extract user data from the log
user_data = extract_user_data_from_log(file_path)

# Print the user data to verify
print(user_data)


# Set up the WebDriver (update the path to your WebDriver if necessary)
driver = webdriver.Chrome()

fields =  [
    {
        'xpath': '//*[@id="formly_33_input_firstName_1"]',
        'value': user_data['first_name'],
    },
    {
        'xpath':  '//*[@id="formly_33_input_surname_2"]',
        'value': user_data['last_name'],
    },
    {
        'xpath':  '//*[@id="formly_33_input_mobileNumber_3"]',
        'value': user_data['contact'],
    },
    {
        'xpath': '//*[@id="formly_33_input_email_5"]',
        'value': user_data['email']
    }
]

repair_type = {
    'Home': '//*[@id="formly_66_radio_homeCommon_1_0"]',
    'Common': '//*[@id="formly_66_radio_homeCommon_1_1"]'
}

try:
    # Open the website
    driver.get('https://maintenance.forms.homes.vic.gov.au/')
    
    # Fill in the other fields
    for field in fields:
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, field['xpath']))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        element.send_keys(field['value'])

    # Wait for the page to load completely
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'p-autocomplete input.p-autocomplete-input'))
    )
    
    # Locate the address input field using the appropriate CSS Selector
    address_input = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'p-autocomplete input.p-autocomplete-input'))
    )

    # Scroll to the email field (to ensure both the email and address fields are in view)
    email_field = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="formly_33_input_email_5"]'))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", email_field)
    time.sleep(1)

    # Use JavaScript to send the address value and trigger the autocomplete
    address_input.clear()
    address_input.send_keys(user_data['address'])  # Input only part of the address to trigger the autocomplete

    # Wait for the dropdown to appear (wait for the ul element of the autocomplete dropdown)
    try:
        dropdown = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'ul.p-autocomplete-items'))
        )

        # Wait for the first item to be clickable and select it
        first_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'ul.p-autocomplete-items li'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", first_option)
        first_option.click()  # Select the first option from the dropdown
    except TimeoutException:
        print("Dropdown menu did not appear or there was an issue selecting the first item.")
    
    time.sleep(2)

    # Scroll to the repair type section
    repair_type_checkbox = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, repair_type[user_data['repair_type']]))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", repair_type_checkbox)
    time.sleep(1)

    # Try clicking the repair type checkbox and handle click interception
    try:
        repair_type_checkbox.click()
    except ElementClickInterceptedException:
        print("Click intercepted! Trying to click using JavaScript...")
        driver.execute_script("arguments[0].click();", repair_type_checkbox)

    time.sleep(2)
        
    #If the repair type is Common
    if user_data['repair_type'] == 'Common':
        # Issue Location
        dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_commonRepairLocation_7']//div[@role='button']"
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", dropdown_trigger)
        time.sleep(2)
        dropdown_trigger.click()

        issue_location_option_xpath = f"//p-dropdown[@id='formly_66_select_commonRepairLocation_7']//p-overlay//span[contains(text(), '{user_data['issue_location']}')]"
        issue_location_option = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, issue_location_option_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", issue_location_option)
        issue_location_option.click()
        
        
        # Issue Area Dropdown
        dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_commonRepairArea_9']//div[@role='button']"
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
        )
        dropdown_trigger.click()

        issue_area_option_xpath = f"//p-dropdown[@id='formly_66_select_commonRepairArea_9']//p-overlay//span[contains(text(), '{user_data['issue_area']}')]"
        issue_area_option = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, issue_area_option_xpath))
        )
        issue_area_option.click()
        
        
        # Issue Type
        dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_commonRepairIssueRelateTo_10']//div[@role='button']"
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
        )
        dropdown_trigger.click()

        issue_type_option_xpath = f"//p-dropdown[@id='formly_66_select_commonRepairIssueRelateTo_10']//p-overlay//span[contains(text(), '{user_data['issue_type']}')]"
        issue_type_option = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, issue_type_option_xpath))
        )
        issue_type_option.click()
    else: # If the repair type is My Home
        # Issue Location
        dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_homeRepairLocation_2']//div[@role='button']"
        issue_location_option_xpath = f"//p-dropdown[@id='formly_66_select_homeRepairLocation_2']//p-overlay//span[contains(text(), '{user_data['issue_location']}')]"
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", dropdown_trigger)
        time.sleep(2)  
        dropdown_trigger.click()
        issue_location_option = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, issue_location_option_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", issue_location_option)
        issue_location_option.click()
        
        # Issue Area Dropdown
        dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_homeRepairRoomArea_3']//div[@role='button']"
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
        )
        dropdown_trigger.click()

        issue_area_option_xpath = f"//p-dropdown[@id='formly_66_select_homeRepairRoomArea_3']//p-overlay//span[contains(text(), '{user_data['issue_area']}')]"
        issue_area_option = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, issue_area_option_xpath))
        )
        issue_area_option.click()
        
        # Issue Type
        dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_homeRepairIssueRelateTo_4']//div[@role='button']"
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
        )
        dropdown_trigger.click()

        issue_type_option_xpath = f"//p-dropdown[@id='formly_66_select_homeRepairIssueRelateTo_4']//p-overlay//span[contains(text(), '{user_data['issue_type']}')]"
        issue_type_option = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, issue_type_option_xpath))
        )
        issue_type_option.click()

        # Dropdown for "Issue Detail Option"
        dropdown_trigger_xpath = "//p-dropdown[@id='formly_66_select_homeOutsideRepairIssue_6']//div[@role='button']"
        issue_detail_option_xpath = f"//p-dropdown[@id='formly_66_select_homeOutsideRepairIssue_6']//p-overlay//span[contains(text(), '{user_data['issue_detail_option']}')]"
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, dropdown_trigger_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", dropdown_trigger)
        time.sleep(1)  # Optional delay for smooth interaction
        dropdown_trigger.click()

        issue_detail_option = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, issue_detail_option_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", issue_detail_option)
        issue_detail_option.click()

        # Checkbox for "Issue Raised in the Last Six Months"
        # Checkbox for "Issue Raised in the Last Six Months" (Click using JavaScript)
        checkbox_xpath = "//input[@id='formly_66_multicheckbox_issueRaisedInTheLastSixMonths_13_0']"
        checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, checkbox_xpath))
        )

        driver.execute_script("arguments[0].click();", checkbox)


        # Text Input for "Tell Us More"
        textarea_xpath = "//textarea[@id='formly_66_textarea_tellUsMore_18']"
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, textarea_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", textarea)
        time.sleep(1)  # Optional delay for smooth interaction
        textarea.clear()  # Clear any pre-existing text
        textarea.send_keys(user_data["issue_text"])

    # Keep the script running to allow you to see the form
    while True:
        pass

except Exception as e:
    print(e)
    # driver.quit()