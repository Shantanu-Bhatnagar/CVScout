import pandas as pd


def jsonl_to_csv(jsonl_file_path, csv_file_path):
    try:
        # Load the JSONL file. 'lines=True' tells pandas to read it line-by-line.
        df = pd.read_json(jsonl_file_path, lines=True)

        # Save the DataFrame to a CSV file
        df.to_csv(csv_file_path, index=False)

        print(
            f"Success! '{jsonl_file_path}' has been converted to '{csv_file_path}'."
        )

    except Exception as e:
        print(f"An error occurred: {e}")


# --- Example Usage ---
input_jsonl = "candidates.jsonl"
output_csv = "data.csv"

jsonl_to_csv(input_jsonl, output_csv)