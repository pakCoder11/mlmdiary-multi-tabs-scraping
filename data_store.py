import json
import pandas as pd
import re
import os

def clean_data(df):
    # Drop rows where all values are null
    cleaned_df = df.dropna()

    return cleaned_df

    # Save the cleaned DataFrame to a file
    # cleaned_df.to_excel(output_file, index=False)  # Change the filename and format as needed

def store_to_json(dict_data, file_path):
    # Open the file in append mode
    with open(file_path, 'a') as f:
        # Use json.dump to write the dictionary to the file
        json.dump(dict_data, f)
        # Write a newline character after each dictionary
        f.write('\n')

def read_dicts_from_json(file_path):
    dicts = []
    with open(file_path, 'r') as f:
        for line in f:
            dicts.append(json.loads(line))
    return dicts

def json_to_excel(json_file_path, excel_file_path):
    # Read the JSON file into a DataFrame
    df = pd.read_json(json_file_path, lines=True)

    # Write the DataFrame to an Excel file
    df.to_excel(excel_file_path, index=False)

def data_storage(main_list):
    # Convert list of lists into a single list
    single_list = [item for sublist in main_list for item in sublist]
    
    # Create a DataFrame from the list
    df = pd.DataFrame(single_list)
    # main_df = clean_data(df)
    
    # Save the DataFrame to an Excel file
    df.to_excel('insta-viral-posts-data.xlsx', index=False)

def save_data_to_excel(input_file_name, output_file_name):

    # Check if data.json exists and is not empty
    if os.path.exists(input_file_name) and os.path.getsize(input_file_name) > 0:
        with open(input_file_name, 'r') as f:
            data = [json.loads(line) for line in f.readlines()]

        # Create a DataFrame from the data
        df = pd.DataFrame(data)
        # Save the DataFrame to an Excel file
        df.to_excel(output_file_name, index=False)

        # Delete the original data.json file
    else:
        print(f"{input_file_name} does not exist or is empty.")

# save_data_to_excel('mlmdiary-profiles-data.json','SAMPLE DATA.xlsx')