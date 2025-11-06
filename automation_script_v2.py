import time
from extract_data import extract_user_data_from_transcript_gpt, translate_improve_transcript
from fill_form_details import *
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
import os,sys,platform,glob


def read_log_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        file_data = file.read()
    return file_data


def extract_user_data(file_data):
    extracted_data = extract_user_data_from_transcript_gpt(file_data)
    user_data = {
        "first_name": extracted_data.first_name,
        "last_name": extracted_data.last_name,
        "contact": extracted_data.contact,
        "email": extracted_data.email,
        "address": extracted_data.address,
        "repair_type": extracted_data.repair_type,
        "issue_location": extracted_data.repair_location,
        "issue_area": extracted_data.issue_area,
        "issue_type": extracted_data.issue_type,
        "issue_detail": extracted_data.issue_detail or "Other",
        "issue_raised": extracted_data.issue_raised,
        "issue_text": extracted_data.issue_additional_details,
        "common_area": extracted_data.common_area,
        "common_inside_floor": extracted_data.common_inside_floor
    }
    return user_data


def setup_webdriver():
    driver = webdriver.Chrome()
    return driver

def fill_details(user_data):
    try:
        driver = setup_webdriver()
        driver.get('https://maintenance.forms.homes.vic.gov.au/')
        
        simple_form_details(driver, user_data)   
        #If the repair type is Common
        if user_data['repair_type'] == 'Common':
            common_form_details(driver, user_data)        
        else: # If the repair type is My Home
            home_form_details(driver, user_data)

        while True:
            pass
    except Exception as e:
        print(e)

def main():
    # Define available languages and their corresponding folders
    language_folders = {
        '1': {
            'name': 'English',
            'folder': '../assets/English'
        },
        '2': {
            'name': 'Bahasa',
            'folder': '../assets/Bahasa'
        },
        '3': {
            'name': 'Vietnamese',                     
            'folder': '../assets/Vietnamese'
        }
    }
    # Change directory if running on macOS (Darwin)
    if platform.system() == "Darwin":
        dir = os.path.sep.join(sys.argv[0].split(os.path.sep)[:-1])
        os.chdir(dir)
    # Step 1: Select the language
    while True:
        print("Please select a language by entering the corresponding number:")
        for key, lang in language_folders.items():
            print(f"{key}. {lang['name']}")
        language_choice = input("Enter 1, 2, or 3,: ").strip()
        if language_choice in language_folders:
            break  # Exit the loop when valid input is provided
        else:
            print("Invalid language selection. Please try again.")
    selected_language = language_folders[language_choice]
    print(f"Selected Language: {selected_language['name']}")
    # Step 2: List available log files in the selected folder
    folder_path = selected_language['folder']
    log_files = glob.glob(os.path.join(folder_path, '*.txt'))
    if not log_files:
        print(f"No log files found in the folder for {selected_language['name']}.")
        return
    log_files = sorted(log_files)  # Sort the files alphabetically
    # Display the available files
    while True:
        print(f"\nPlease select a log file for {selected_language['name']} by entering the corresponding number:")
        for i, file_path in enumerate(log_files, 1):
            file_name = os.path.basename(file_path)
            print(f"{i}. {file_name}")
        file_choice = input(f"Enter a number between 1 and {len(log_files)}: ").strip()
        try:
            file_choice_index = int(file_choice) - 1
            if 0 <= file_choice_index < len(log_files):
                break  # Exit the loop when valid input is provided
            else:
                print("Invalid file selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")
    selected_file = log_files[file_choice_index]
    print(f"Selected File: {selected_file}")
    # Step 3: Read the log file and process the data
    try:
        file_data = read_log_file(selected_file)
        # print("File Data:", file_data)
        improved_transcript = translate_improve_transcript(file_data)
        # print("Improved Transcript:", improved_transcript)
        user_data = extract_user_data(improved_transcript)
        print("User Data:", user_data)
        # comment the following line to avoid populating the form with extracted user data
        fill_details(user_data)
    except FileNotFoundError:
        print(f"Error: The file {selected_file} was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
