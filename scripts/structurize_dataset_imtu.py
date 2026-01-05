import os
import csv

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, 'imtu_ym.txt')
    output_path = os.path.join(script_dir, 'imtu_ym.o.txt')

    print(f"Reading from {input_path}")
    print(f"Writing to {output_path}")

    processed_rows = []

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                
                if len(parts) < 2:
                    print(f"Skipping malformed line: {line}")
                    continue

                try:
                    year = int(parts[0])
                    month = int(parts[1])
                    rest_values = parts[2:]
                    
                    total_months = year * 12 + month
                    
                    new_row = [str(total_months)] + rest_values
                    processed_rows.append(new_row)
                    
                except ValueError as e:
                    print(f"Error parsing line '{line}': {e}")
                    continue
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(processed_rows)
            
        print("Conversion complete.")

    except FileNotFoundError:
        print(f"Error: The file {input_path} was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
