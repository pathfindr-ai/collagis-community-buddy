import os
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from dotenv import load_dotenv
load_dotenv()

client = OpenAI()  # Will use OPENAI_API_KEY environment variable
from mappings import (
    common_outside_issue_area,
    common_inside_issue_area,
    home_inside_issue_area,
    issue_type,
    common_outside_access_issues,
    common_inside_access_issues,
    home_inside_access_issues,
    common_outside_cleaning_issues,
    common_inside_cleaning_issues,
    home_inside_cleaning_issues,
    common_outside_electrical_issues,
    common_inside_electrical_issues,
    home_inside_electrical_issues,
    common_outside_gas_issues,
    common_inside_gas_issues,
    home_inside_gas_issues,
    common_outside_water_issues,
    common_inside_water_issues,
    home_inside_water_issues,
    common_outside_something_else_issues,
    common_inside_something_else_issues,
    home_inside_something_else_issues,
    home_outside_access_issues,
    home_outside_cleaning_issues,
    home_outside_electrical_issues,
    home_outside_gas_issues,
    home_outside_issue_area,
    home_outside_something_else_issues,
    home_outside_water_issues
)


class UserData(BaseModel):
    first_name: str  
    last_name: str
    contact: str = Field(description = "it should be number like 0123456789")
    email: str
    address: str
    common_inside_floor: str = Field(description="It should be 'Ground' or a floor number (1 to 50) for common inside location otherwise it should be None.")
    repair_type: Literal['Home', 'Common']
    repair_location: Literal['Inside', 'Outside']
    issue_area: str
    issue_type: Literal['Access','Cleaning','Electrical','Gas','Water','Something else']
    issue_raised: Literal['Yes','No']
    issue_detail: str
    issue_additional_details: str
    common_area: str

    @field_validator('common_inside_floor')
    def validate_floor(cls, value):
        if value == "None" or "Nothing":
            return value
        # Check if it's 'Ground'
        elif value == "Ground":
            return value
        # Check if it's a valid floor number between 1 and 50
        elif value.isdigit() and 1 <= int(value) <= 50:
            return value
        raise ValueError('common_inside_floor must be "Ground" or a floor number between 1 and 50')

def format_mappings_for_prompt() -> str:
    return f"""
    The following are the mappings to use for extracting the issue_area:

    
    Common Outside Issue Area: {common_outside_issue_area}
    Common Inside Issue Area: {common_inside_issue_area}
    Home Inside Issue Area: {home_inside_issue_area}
    Home Outside Issue Area: {home_outside_issue_area}

    The following are the mappings to use for extracting the issue_type

    Issue Type: {issue_type}

    The following are the mappings to use for extracting the issue_detail variable:

    Common Outside Access Issues: {common_outside_access_issues}
    Common Inside Access Issues: {common_inside_access_issues}
    Home Inside Access Issues: {home_inside_access_issues}
    Home Outside Access Issues: {home_outside_access_issues}
    Common Outside Cleaning Issues: {common_outside_cleaning_issues}
    Common Inside Cleaning Issues: {common_inside_cleaning_issues}
    Home Inside Cleaning Issues: {home_inside_cleaning_issues}
    Home Outside Cleaning Issues: {home_outside_cleaning_issues}
    Common Outside Electrical Issues: {common_outside_electrical_issues}
    Common Inside Electrical Issues: {common_inside_electrical_issues}
    Home Inside Electrical Issues: {home_inside_electrical_issues}
    Home Outside Electrical Issues: {home_outside_electrical_issues}
    Common Outside Gas Issues: {common_outside_gas_issues}
    Common Inside Gas Issues: {common_inside_gas_issues}
    Home Inside Gas Issues: {home_inside_gas_issues}
    Home Outside Gas Issues: {home_outside_gas_issues}
    Common Outside Water Issues: {common_outside_water_issues}
    Common Inside Water Issues: {common_inside_water_issues}
    Home Inside Water Issues: {home_inside_water_issues}
    Home Outside Water Issues: {home_outside_water_issues}
    Common Outside Something Else Issues: {common_outside_something_else_issues}
    Common Inside Something Else Issues: {common_inside_something_else_issues}
    Home Inside Something Else Issues: {home_inside_something_else_issues}
    Home Outside Something Else Issues: {home_outside_something_else_issues}
    """


# Function to send transcript to GPT and extract information in JSON format
def extract_user_data_from_transcript_gpt(transcript: str) -> dict:
    mappings_description = format_mappings_for_prompt()
    # print(mappings_description)
    print("Requesting LLM to extract the data...")
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06", 
        messages=[
            {
            "role": "system",
            "content": f"""
            You are an assistant designed to extract specific information from a provided transcript. **Strictly adhere** to the following instructions to ensure accuracy and consistency.

            **Response Format**:
            - Respond **only** with a JSON object containing the following fields:
                - `issue_detail`: Must be **exactly one** of the options provided in the mappings. If none apply, set to `"Other"`.
                - `common_area`: Extract any mention that helps locate the common area. If none, set to `"Nothing"`.
                - `common_inside_floor`: If the user lives in a high-rise building and mentions a floor number, extract it. If unspecified or unsure, set to `"Ground"`.
                - `issue_text`: Include **only** additional relevant details from the transcript.

            **Mappings**:
            {mappings_description}

            **Extraction Rules**:

            1. **issue_detail**:
            - **Mandatory**: Select **only one** option from the provided mappings.
            - **No Exceptions**: Do **not** infer, combine, or create new categories.
            - If no mapping fits, **solely** set `issue_detail` to `"Other"`.

            2. **common_area**:
            - Extract any specific details that help identify the common area.
            - If absent, **only** set to `"Nothing"`.

            3. **common_inside_floor**:
            - Determine if the user resides in a high-rise building.
            - If yes and a floor number is mentioned, extract it.
            - If the floor number is not specified or the user is unsure, **only** set to `"Ground"`.

            4. **issue_text**:
            - Include **only** additional relevant details mentioned by the user.
            - Do **not** add any inferred or unrelated information.

            5. **email**:
            - Extract the user's email address from the transcript.
            - Ensure that the extracted email follows standard email syntax (e.g., contains exactly one `@`, has a valid domain, etc.).
            - If the email in the transcript is malformed, **correct** it to adhere to standard email formatting rules .

            **Important Constraints**:
            - **Do Not**:
                - Provide explanations, comments, or additional text outside the JSON object.
                - Infer or assume information not explicitly stated in the transcript.
                - Deviate from the specified response format.

            - **Must**:
                - Ensure the JSON object includes **all** specified fields.
                - Follow the mappings **exclusively** for `issue_detail`.
                - Use exact field names and structure as specified.
                - Validate and correct the `email` field to ensure it adheres to standard email formatting rules.

            **Transcript Analysis**:
            Analyze the following transcript and extract the required information **strictly** according to the rules above.

            """
            },
            {"role": "user", "content": transcript},
            # {"role": "user", "content": mappings_description},
        ],
        temperature=0,
        response_format=UserData,
    )
    print("Relevant data extracted from the transcript...")
    return completion.choices[0].message.parsed

# Function to send transcript to GPT and tranlate it
def translate_improve_transcript(transcript: str):
    # print(mappings_description)
    print("Cleaning the given transcription...")
    completion = client.beta.chat.completions.parse(
        # model="gpt-4o-mini-2024-07-18", 
        model="gpt-4o-2024-08-06", 
        messages=[
            # {"role": "system", "content": f"""
            # You have been provided with the transcript. translate the provided transcript to English language.
            # Improve any lingual mistakes in the trascript.
            # Provide me the translated and improved transcript in same format as provided transcript. Don't alter critical information.
            # """},
            {
                    "role": "system",
                    "content": f"""
            You are an assistant specialized in translating and refining transcripts. **Follow the instructions below precisely** to ensure accurate and consistent outputs.

            **Task Overview**:
            - **Primary Objective**: Translate non-English transcripts to English.
            - **Secondary Objective**: Correct typos, transcription errors, and regional or accent-related mistakes in non-English transcripts.

            **Detailed Instructions**:

            1. **Language Detection**:
                - **Check** if the provided transcript is in English.
                    - **If English**:
                        - **Do Not Alter** the transcript.
                        - **Return** the transcript exactly as provided.
                    - **If Not English**:
                        - **Proceed** to the Translation and Improvement steps.

            2. **Translation and Improvement** (For Non-English Transcripts Only):
                - **Translate** the entire transcript to English.
                - **Correct** any:
                    - **Typos**
                    - **Transcription Mistakes**
                    - **Regional or Accent-Related Errors**
                - **Ensure** that **no critical information** is altered or omitted during translation and correction.

            3. **Format Preservation**:
                - **Maintain** the original format of the transcript (e.g., timestamps, speaker labels, paragraphs).
                - **Ensure** that the translated and improved transcript mirrors the structure of the original.

            4. **Output Guidelines**:
                - **Respond Only** with the translated and/or improved transcript.
                - **Do Not Include** any additional text, explanations, comments, or examples outside the translated/improved transcript.
                - **Ensure** the output is clean and free from any markup or annotations unless present in the original transcript.
                - **Maintain Exact Format**: The output must strictly follow the same formatting as the input transcript without any deviations.

            **Important Constraints**:
            - **Do Not**:
                - Translate transcripts that are already in English.
                - Alter or omit any critical information from the original transcript.
                - Provide explanations, comments, additional text, or examples outside the translated/improved transcript.
                - Include any few-shot learning examples or sample inputs/outputs.
            
            - **Must**:
                - Accurately detect the language of the transcript.
                - Follow the original format and structure of the transcript meticulously.
                - Ensure high-quality translation and correction without introducing errors.
            """},
            {"role": "user", "content": transcript},
            # {"role": "user", "content": mappings_description},
        ],
        temperature=0.2,
    )
    print("Transcript is cleaned...")
    return completion.choices[0].message.content