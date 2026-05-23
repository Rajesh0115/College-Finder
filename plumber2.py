import pdfplumber
import pandas as pd
import re

pdf_file = r"D:\Admin\Documents\FILES\CODES\python\ml\data_extraction\cutoff_2025_cap4.pdf"
extracted_data = []

current_college = None
current_branch = None

def roman_to_int(roman):
    roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5}
    return roman_map.get(roman.upper(), roman)

with pdfplumber.open(pdf_file) as pdf:
    first_page_text = pdf.pages[0].extract_text()

    year_match = re.search(r'Year[\s\n]+(\d{4})', first_page_text, re.IGNORECASE)
    dynamic_year = int(year_match.group(1)) if year_match else None
    
    round_match = re.search(r'CAP[\s\n]+Round[\s\n\-]*([IVX]+|\d+)', first_page_text, re.IGNORECASE)
    dynamic_round = roman_to_int(round_match.group(1)) if round_match else None
    
    print(f"Detected Year: {dynamic_year} | Detected Round: {dynamic_round}")

    for page in pdf.pages:
        text_lines = page.extract_text_lines()
        tables = page.find_tables()
        
        elements = []
        for line in text_lines:
            elements.append({'type': 'text', 'top': line['top'], 'data': line['text'].strip()})
            
        for table in tables:
            elements.append({'type': 'table', 'top': table.bbox[1], 'data': table.extract()})
            
        elements.sort(key=lambda x: x['top'])
        
        for el in elements:
            if el['type'] == 'text':
                text = el['data']
                if re.match(r'^\d{4,5}\s*-', text):
                    current_college = text
                elif re.match(r'^\d{9,10}\s*-', text):
                    current_branch = text
                    
            elif el['type'] == 'table':
                table_data = el['data']
                if not table_data or len(table_data) < 2:
                    continue
                
                headers = [str(h).replace('\n', '').strip() if h else "" for h in table_data[0]]
                
                for row in table_data[1:]:
                    for col_idx in range(1, len(row)):
                        cell = row[col_idx]
                        category = headers[col_idx]
                        
                        if not cell or not category:
                            continue
                            
                        cell_parts = str(cell).strip().split('\n')
                        
                        if len(cell_parts) >= 2:
                            rank = re.sub(r'[^\d]', '', cell_parts[0])
                            
                            percentile_str = "".join(cell_parts[1:])
                            percentile_str = percentile_str.replace(' ', '.')
                            percentile = re.sub(r'[^\d\.]', '', percentile_str)
                            
                            if rank and percentile:
                                extracted_data.append({
                                    'year': 2025,
                                    'cap_round': 4,
                                    'college': current_college,
                                    'branch': current_branch,
                                    'cateogory': category,
                                    'cutoff_percentile': percentile,
                                    'rank': rank
                                })

df = pd.DataFrame(extracted_data)

target_columns = ['year', 'cap_round', 'college', 'branch', 'cateogory', 'cutoff_percentile', 'rank']
df = df[target_columns]

df.to_csv("final_cutoffs_2025_cap4.csv", index=False)