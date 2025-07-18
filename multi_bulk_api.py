import re
from flask import Flask, request, jsonify, render_template
import fitz
from PIL import Image
import io
import numpy as np
from paddleocr import PaddleOCR
import pytesseract
from PIL import ImageOps, ImageFilter

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('bulk_upload.html')

def convert_pdf_to_image_tesseract(pdf_data):
    # zoom_x = 16.0
    # zoom_y = 16.0
    # mat = fitz.Matrix(zoom_x, zoom_y)

    # doc = fitz.open(pdf_data)
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(colorspace='gray',
                          dpi=330) # 330

    img_data = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_data))

    return image

def extract_text_with_tesseract(image):
    custom_oem_psm_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(image, lang='ara+eng', config=custom_oem_psm_config)
    return text.splitlines()


def convert_pdf_to_image(pdf_data):
    zoom_x = 16.0
    zoom_y = 16.0
    mat = fitz.Matrix(zoom_x, zoom_y)

    doc = fitz.open(stream=pdf_data, filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=mat, colorspace='gray')

    img_data = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_data))

    return np.array(image)

def find_address_line(lines):
    for line in lines:
        if "العنوان" in line and "Address" in line:
            return line
    return None

def extract_address(text):
    parts = text.split("العنوان")
    if len(parts) > 1:
        address_parts = parts[1].split("Address")
        if address_parts and len(address_parts) > 0:
            return address_parts[0].strip()
    return "Address not found."

def extract_invoice_details(text_list):
    invoice_date_en, due_date_en = None, None
    invoice_number, sale_person = None, None
    po_ref, buyer, phone, vat_id, internal_ref= None, None, None, None, None
    nature_of_goods_or_service, quantity, uom, price_unit, tax_amount, subtotal = None, None, None, None, None, None
    total_excluded_vat, disc, total_tax_amount, total_vat, total_amount_due, amt_invoiced, amt_invoiced_ar = None, None, None, None, None, None, None
    notes_ar = None
    add1, add2, add3, add4, bank_num, cr_no, reg_no = None, None, None, None, None, None, None
    sale_person_name = None
    cr_no_pattern = re.compile(r'CR NO:\s*(\d+)')
    bank_num_pattern = re.compile(r'[A-Z]{2}\d{2}[A-Z0-9]{4}\d{16}')
    due_date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
    invoice_number_pattern = re.compile(r'INV/\d{4}/\d+')
    # phone_pattern = re.compile(r'\+\d+')
    phone_pattern = re.compile(r'(?:Phone\s*)?(\+\d+)')
    total_excluded_vat_pattern = re.compile(r'(([\d,]+\.\d{2})\s*SR\s*Total\s*\(?\s*Excluded\s*VAT\s*\)?)|(Total\s*\(?\s*Excluded\s*VAT\s*\)?\s*([\d,]+\.\d{2})\s*SR)')
    total_tax_amount_pattern = re.compile(r'Total\s+Taxable\s+Amount\s+([\d,]+.\d{2})\s*SR')
    # total_vat_pattern = re.compile(r'(?:((?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?)\s*Total\s*VAT)|(Total\s*VAT[^\d]*(\d+(?:\.\d+)?))')
    total_vat_pattern = re.compile(r'(?:\b(\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?\b\s*Total\s*VAT)|(?:Total\s*VAT[^\d]+(\d+(?:\.\d+)?))')
    total_amount_due_pattern = re.compile(r'((?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?)\s*SR\s*Total\s*Amount\s*Due|Total\s*Amount\s*Due\s*[\s\S]*?(\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?\s*SR')
    sale_person_pattern = re.compile(r"إسم البائع\s+.*?(?:Sale|Pale) Person\s+([A-Za-z\s]+)", re.DOTALL)
    customer_pattern = re.compile(r"العميل\s+(.*?)\s*\u200e?Customer\u200f?", re.DOTALL)
    address_pattern = re.compile(r"العنوان\s+(.*?)\s*\u200e?Address\u200f?", re.DOTALL)
    # address_pattern = re.compile(r"Address\s+العنوان\s+(.*)")

    first_line_index = None
    last_line_index = None
    products_info = None
    customer_name = None
    extracted_address = None

    for i, text in enumerate(text_list):

        match = sale_person_pattern.search(text)
        if match:
            sale_person_name = match.group(1).strip()

        match = customer_pattern.search(text)
        if match:
            customer_name = match.group(1).strip()

        address_line = find_address_line(text_list)
        # print("print address line:", address_line)
        if address_line:
            extracted_address = extract_address(address_line)
        # extracted_address = extract_address(text)

        if "الوحدة للضريبة شامل الضريبة" in text and first_line_index is None:
            first_line_index = i
        if re.search(r"Total \( Excluded VAT\).*المبلغ الاجمالى", text):
            last_line_index = i


        if "Invoice Date" in text:
            date_match = date_pattern.search(text)
            if date_match:
                invoice_date_en = date_match.group()
        if "Invoice Number" in text:
            number_match = invoice_number_pattern.search(text)
            if number_match:
                invoice_number = number_match.group()
        elif text == "Sale Person" and i + 1 < len(text_list):
            sale_person = text_list[i + 1]
            sale_person = sale_person.split()
            sale_person = ' '.join(sale_person[:2])
        elif text == "PO Ref":
            po_ref = None
        elif text == "Buyer":
            buyer = None
        elif text == "VAT ID":
            vat_id = None
        elif text == "Internal ref":
            internal_ref = None
        elif text == "otaAmount" and i - 1 >= 0:
            nature_of_goods_or_service = text_list[i - 1]
        elif text == "Total Amounts" and i - 2 >= 0:
            try:
                quantity = float(text_list[i - 2])
            except ValueError:
                quantity = None
        elif text == "Excluded VAT" and i - 7 >= 0:
            uom = text_list[i - 7]
        if text == "Total (Excluded VAT)" and i - 7 >= 0:
            price_unit = text_list[i - 7]
        if text == "Total (Excluded VAT)" and i - 8 >= 0:
            tax_amount = text_list[i - 8]
        if text == "Total (Excluded VAT)" and i - 9 >= 0:
            subtotal = text_list[i - 9]
        vat_match = total_excluded_vat_pattern.search(text)
        if vat_match:
            total_excluded_vat = vat_match.group(2) if vat_match.group(2) else vat_match.group(4)
        if text == "Discount" and i - 2 >= 0:
            disc = text_list[i - 2]
        else:
            disc = float(0.0)
        if text == "This invoice is computer generated print out no signature or stamp is required" and i - 3 >= 0:
            amt_invoiced_raw = text_list[i - 3]
            match = re.search(r".*cent[s]?", amt_invoiced_raw, re.IGNORECASE)
            if match:
                amt_invoiced = match.group(0).strip()
            else:
                amt_invoiced = amt_invoiced_raw.strip()
            amt_invoiced = amt_invoiced.split("$")[0].strip()
        if text == "AMOUNT INVOICED" or text == "AMOUNT" and i - 1 >= 0:
            amt_invoiced_ar = text_list[i - 1]
        if text == "ملحوظات" or text == "ملدوظات" and i - 1 >= 0:
            notes_ar = text_list[i - 1]
        if text == "الصفحة 11:" and i + 2 < len(text_list):
            add1 = text_list[i + 2]
        if text == "الصفحة 11:" and i + 6 < len(text_list):
            add2 = text_list[i + 6]
        if text == "الصفحة 11:" and i + 8 < len(text_list):
            add3 = text_list[i + 8]
        if text == "الصفحة 11:" and i + 10 < len(text_list):
            add4 = text_list[i + 10]
        if text == "a!!n ojgiLa VAT Invoice" or text == "a!!n ojgia VAT Invoice" and i - 1 >= 0:
            reg_no = text_list[i - 1]
        match = cr_no_pattern.search(text)
        if match:
            cr_no = match.group(0)
        bank_match = bank_num_pattern.search(text)
        if bank_match:
            bank_num = bank_match.group(0)

        address_parts = [add1, add2, add3, add4]
        address = " ".join(part for part in address_parts if part is not None)

        if "Due Date" in text:
            date_match = due_date_pattern.search(text)
            if date_match:
                due_date_en = date_match.group()
        phone_match = phone_pattern.search(text)
        if phone_match:
            phone = phone_match.group(1)
        taxable_amount_match = total_tax_amount_pattern.search(text)
        if taxable_amount_match:
            total_tax_amount = taxable_amount_match.group(1)

        vat_match = total_vat_pattern.search(text)
        if vat_match:
            total_vat = vat_match.group(1) if vat_match.group(1) else vat_match.group(2)
        
        total_amount_due_match = total_amount_due_pattern.search(text)
        if total_amount_due_match:
            total_amount_due = total_amount_due_match.group(1) if total_amount_due_match.group(1) else total_amount_due_match.group(2)

    # print("First Line Index:", first_line_index)
    # print("Last Line Index:", last_line_index)

    if first_line_index is not None and last_line_index is not None and first_line_index < last_line_index:
        extracted_strings = text_list[first_line_index+1:last_line_index]
        print(extracted_strings)
        products_info = []

        converted_numbers_lists = [] 
        arabic_product_names = []

        for index, string in enumerate(extracted_strings):
            parts = string.split()
            converted_numbers = []
            arabic_text_parts = []

            for part in parts:
                part_no_commas = part.replace(',', '')
                try:
                    converted = float(part_no_commas)
                    if converted.is_integer():
                        converted = int(converted)
                    converted_numbers.append(converted)
                except ValueError:
                    arabic_text_parts.append(part)
            # print("Arabic Text: ", arabic_text_parts)
            if arabic_text_parts:
                # product_name = ' '.join(arabic_text_parts)
                product_name_full = ' '.join(arabic_text_parts)
                product_name_words = product_name_full.split()

                if len(product_name_words) > 2:
                    product_name = ' '.join(product_name_words[:-2])
                else:
                    product_name = product_name_full


                arabic_product_names.append(product_name)
            
            converted_numbers.sort(reverse=True)

            if converted_numbers:
                converted_numbers_lists.append(converted_numbers)

        converted_numbers_iteration_count = len(converted_numbers_lists)
        # print("Converted Numbers Iterated:", converted_numbers_iteration_count)

        # products_names_list = product_names if converted_numbers_iteration_count == len(product_names) else product_names1
        # products_names_list = product_names if converted_numbers_iteration_count == len(product_names) else (product_names1 if len(product_names1) else product_names2)
        # if converted_numbers_iteration_count == len(product_names):
        #     products_names_list = product_names
        # else:
        #     products_names_list = product_names1

        products_info = []
    
        for i, converted_numbers in enumerate(converted_numbers_lists):
            subtotal = converted_numbers[0] if len(converted_numbers) > 0 else None
            tax_amount = converted_numbers[1] if len(converted_numbers) > 1 else None
            price_unit = converted_numbers[2] if len(converted_numbers) > 2 else None
            quantity = tax_amount / price_unit if price_unit and tax_amount else None

            # product_name_index = i % len(arabic_text_parts)
            # product_name = arabic_text_parts[product_name_index]

            product_name = arabic_product_names[i] if i < len(arabic_product_names) else "Unknown Product"

            product_details = {
                "Nature of Goods or service (تفاصيل السلع أو الخدمات)": product_name,
                "Subtotal (Including VAT) (الاجمالي شامل الضريبة)": subtotal,
                "Tax Amount (المبلغ الخاضع للضريبة)": tax_amount,
                "Price Unit (سعر الوحدة)": price_unit,
                "Quantity (الكمية)": quantity,
            }
            products_info.append(product_details)

        if not products_info:
            products_info.append({
                "Nature of Goods or service (تفاصيل السلع أو الخدمات)": nature_of_goods_or_service,
                "Subtotal (Including VAT) (الاجمالي شامل الضريبة)": float(total_amount_due) if total_amount_due else 0,
                "Tax Amount (المبلغ الخاضع للضريبة)": float(total_excluded_vat) if total_excluded_vat else 0,
                "Price Unit (سعر الوحدة)": float(total_excluded_vat) if total_excluded_vat else 0,
                "Quantity (الكمية)": int(float(total_excluded_vat))/int(float(total_excluded_vat))
            })


    # print("Here is the Product:", products_names_list)

    return {
        "Invoice Date (تاريخ الفاتورة)": invoice_date_en,
        "Due Date (تاريخ الاستحقاق)": due_date_en,
        "Invoice No. (رقم الفاتورة)": invoice_number,
        "Sale Person (اسم البائع)": sale_person_name,
        "PO Ref (مرجع طلب الشراء)": po_ref,
        "Buyer (العميل)": buyer,
        # "Phone (هاتف)": phone,
        "Phone (هاتف)": phone,
        "VAT ID (الرقم الضريبي)": vat_id,
        "Internal ref (المرجع الداخلي)": internal_ref,
        # "Nature of Goods or Service (تفاصيل السلع أو الخدمات)": nature_of_goods_or_service,
        # "Quantity (الكمية)": quantity,
        # "UoM (الوحدة)": uom,
        # "Products": products,
        # "Price Unit (سعر الوحدة)": price_unit,
        # "Tax Amount (المبلغ الخاضع للضريبة)": tax_amount,
        # "Subtotal Including VAT (الاجمالي شامل الضريبة)": subtotal,
        "Total (Excluded VAT) (المبلغ الاجمالى))": total_excluded_vat,
        "Discount (مجموع الخصم)": disc,
        "Total Taxable Amount (الاجمالى الخاضع للضريبة)": total_excluded_vat,
        "Total VAT (قيمة الضريبة المضافة)": total_vat,
        "Total Amount Due (إجمالي المبلغ المستحق)": total_amount_due,
        "Amount Invoiced (قيمة الفاتورة)": amt_invoiced,
        "قيمة الفاتورة": amt_invoiced_ar,
        "ملحوظات": notes_ar,
        # "Address (English)": address,
        "Bank Number (بنك الانماء)": bank_num,
        "CR Number": cr_no,
        "رقم تسجيل ضريبة القيمة المضافة": reg_no,
        "Customer (العميل)": customer_name,
        "Address (العنوان)": extracted_address,
        "Other Details": text_list[-2:-1],
        "Products Info": products_info,
        "Notes": text_list[-3:-2]
        }

@app.route('/upload', methods=['POST'])
def upload_file():
    files = request.files.getlist('file')
    if not files:
        return jsonify({"error": "No files were uploaded"}), 400

    results = []

    for file in files:
        if file and file.filename.endswith('.pdf'):
            file_content = file.read()
            try:
                image = convert_pdf_to_image(file_content)
                image_for_tesseract = convert_pdf_to_image_tesseract(file_content)

                ocr_ar = PaddleOCR(use_gpu=False, lang="ar")
                ocr_en = PaddleOCR(use_gpu=False, lang="en")
                results_ar = ocr_ar.ocr(image, cls=True)
                results_en = ocr_en.ocr(image, cls=True)

            # def extract_text(results):
            #     recognized_text = []
            #     for page_result in results:
            #         for element in page_result:
            #             text = element[1][0]
            #             recognized_text.append(text)
            #     return recognized_text

                def is_arabic(text):
                    """Simple heuristic to check if the text contains Arabic characters."""
                    arabic_range = range(0x0600, 0x06FF)
                    for character in text:
                        if ord(character) in arabic_range:
                            return True
                    return False

                def should_merge(previous_position, current_position):
                    """Determines whether two text blocks should be merged based on their positions."""
                    previous_mid_y = (previous_position[0][1] + previous_position[3][1]) / 2
                    current_mid_y = (current_position[0][1] + current_position[3][1]) / 2

                    y_threshold = 20

                    if abs(previous_mid_y - current_mid_y) <= y_threshold:
                        return True
                    return False

                def extract_text(results):
                    """Extracts and merges text from OCR results, considering script directionality and spatial proximity."""
                    merged_text = []
                    current_text = ""
                    last_position = None
                    is_last_text_arabic = False

                    for page_result in results:
                        for element in page_result:
                            text, position = element[1][0], element[0]
                            is_current_text_arabic = is_arabic(text)

                            if last_position and should_merge(last_position, position):
                                if is_current_text_arabic == is_last_text_arabic:
                                    if is_current_text_arabic:
                                        current_text = text + " " + current_text
                                    else:
                                        current_text += " " + text
                                else:
                                    merged_text.append(current_text)
                                    current_text = text
                            else:
                                if current_text:
                                    merged_text.append(current_text)
                                current_text = text

                            last_position = position
                            is_last_text_arabic = is_current_text_arabic

                    if current_text:
                        merged_text.append(current_text)

                    return merged_text

                recognized_text_ar = extract_text(results_ar)
                recognized_text_en = extract_text(results_en)
                recognized_text_tesseract = extract_text_with_tesseract(image_for_tesseract)

                arabic_addresses = []
                english_addresses = []

                first_six_lines = recognized_text_tesseract[:6]

                for line in first_six_lines:
                    arabic_parts = re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+', line)
                    english_parts = re.findall(r'[A-Za-z0-9,.\s]+', line)
                    
                    arabic_address = ' '.join(arabic_parts).strip()
                    english_address = ' '.join(english_parts).strip()
                    
                    if arabic_address:
                        arabic_addresses.append(arabic_address)
                    if english_address:
                        english_addresses.append(english_address)

                    full_arabic_address = ', '.join(arabic_addresses[1:])
                    full_english_address = ', '.join(english_addresses[1:])
                
                # print("Arabic Addresses:", full_arabic_address)
                # print("English Addresses:", full_english_address)
                # print(recognized_text_tesseract)

                merged_results = recognized_text_ar + recognized_text_en + recognized_text_tesseract
                extracted_details = extract_invoice_details(merged_results)
                extracted_details["Address (Arabic)"] = full_arabic_address
                extracted_details["Address (English)"] = full_english_address

                file_result = {
                    "file_name": file.filename,
                    "extracted details": extracted_details
                    # "Merged Text": merged_results
                }
                results.append(file_result)

            except Exception as e:
                return jsonify({"error": f"Error processing file {file.filename}: {str(e)}"}), 500
        else:
            return jsonify({"error": f"Invalid file format for {file.filename}. Only PDF files are supported."}), 400

    return jsonify({"results": results}), 200

if __name__ == '__main__':
    app.run(debug=True)
