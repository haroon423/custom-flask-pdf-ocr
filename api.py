import re
from flask import Flask, request, jsonify, render_template
import fitz
from PIL import Image
import io
import numpy as np
from paddleocr import PaddleOCR

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('upload.html')

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

def extract_invoice_details(text_list):
    invoice_date_en, due_date_en = None, None
    invoice_number, sale_person = None, None
    po_ref, buyer, phone, vat_id, internal_ref= None, None, None, None, None
    nature_of_goods_or_service, quantity, uom, price_unit, tax_amount, subtotal = None, None, None, None, None, None
    total_excluded_vat, disc, total_tax_amount, total_vat, total_amount_due, amt_invoiced, amt_invoiced_ar = None, None, None, None, None, None, None
    notes_ar, note_en = None, None
    add1, add2, add3, add4, bank_num, cr_no, reg_no = None, None, None, None, None, None, None
    cr_no_pattern = re.compile(r'CR NO:\s*(\d+)')
    

    for i, text in enumerate(text_list):
        if text == "Invoice Date" and i + 1 < len(text_list):
            invoice_date_en = text_list[i + 1]
        elif text == "Due Date" and i + 2 < len(text_list):
            due_date_en = text_list[i + 2]
        elif re.match(r'^INV/', text):
            invoice_number = text
        elif text == "Sale Person" and i + 1 < len(text_list):
            sale_person = text_list[i + 1]
        elif text == "PO Ref":
            po_ref = None
        elif text == "Buyer":
            buyer = None
        elif text == "Phone" and i - 2 >= 0 and re.match(r'^\+', text_list[i - 2]):
            phone = text_list[i - 2]
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
        if text == "Total (Excluded VAT)" and i - 1 >= 0:
            total_excluded_vat = text_list[i - 1]
        if text == "Discount" and i - 1 >= 0:
            disc = text_list[i - 1]
        if text == "Total Taxable Amount" and i + 1 >= 0:
            total_tax_amount = text_list[i + 1]
        if text == "Total VAT" and i + 2 >= 0:
            total_vat = text_list[i + 2]
        if text == "Total Amount Due" and i - 1 >= 0:
            total_amount_due = text_list[i - 1]
        if text == "AMOUNT INVOICED" and i - 2 >= 0:
            amt_invoiced = text_list[i - 2]
        if text == "INVOICED" and i + 1 >= 0:
            amt_invoiced_ar = text_list[i + 1]
        if text == "INVOICED" and i + 3 >= 0:
            notes_ar = text_list[i + 3]
        if text == "AMOUNT INVOICED" and i + 4 >= 0:
            notes_en = text_list[i + 4]
        if text == "Invoice Number" and i - 9 < len(text_list):
            add1 = text_list[i - 9]
        if text == "Invoice Number" and i + 11 < len(text_list):
            add2 = text_list[i - 11]
        if text == "Invoice Number" and i + 13 < len(text_list):
            add3 = text_list[i - 13]
        if text == "Invoice Number" and i + 15 < len(text_list):
            add4 = text_list[i - 15]
        if text == "Quantity" and i - 7 < len(text_list):
            bank_num = text_list[i - 7]
        if text == "Invoice Number" and i - 4 < len(text_list):
            reg_no = text_list[i - 4]
        match = cr_no_pattern.search(text)
        if match:
            cr_no = match.group(0)

        address_parts = [add4, add3, add2, add1]
        address = " ".join(part for part in address_parts if part is not None)

    return {
        "Invoice Date (تاريخ الفاتورة)": invoice_date_en,
        "Due Date (تاريخ الاستحقاق)": due_date_en,
        "Invoice No. (رقم الفاتورة)": invoice_number,
        "Sale Person (اسم البائع)": sale_person,
        "PO Ref (مرجع طلب الشراء)": po_ref,
        "Buyer (العميل)": buyer,
        "Phone (هاتف)": phone,
        "VAT ID (الرقم الضريبي)": vat_id,
        "Internal ref (المرجع الداخلي)": internal_ref,
        "Nature of Goods or Service (تفاصيل السلع أو الخدمات)": nature_of_goods_or_service,
        "Quantity (الكمية)": quantity,
        "UoM (الوحدة)": uom,
        "Price Unit (سعر الوحدة)": price_unit,
        "Tax Amount (المبلغ الخاضع للضريبة)": tax_amount,
        "Subtotal Including VAT (الاجمالي شامل الضريبة)": subtotal,
        "Total (Excluded VAT) (المبلغ الاجمالى))": total_excluded_vat,
        "Discount (مجموع الخصم)": disc,
        "Total Taxable Amount (الاجمالى الخاضع للضريبة)": total_tax_amount,
        "Total VAT (قيمة الضريبة المضافة)": total_vat,
        "Total Amount Due (إجمالي المبلغ المستحق)": total_amount_due,
        "Amount Invoiced (قيمة الفاتورة)": amt_invoiced,
        "قيمة الفاتورة": amt_invoiced_ar,
        "ملحوظات": notes_ar,
        "Notes": notes_en,
        "Address (English)": address,
        "Bank Number (بنك الانماء)": bank_num,
        "CR Number": cr_no,
        "رقم تسجيل ضريبة القيمة المضافة": reg_no,
        "Customer (العميل)": "مؤسسة تجلى العربية للدعايةوالاعلان",
        "Address (العنوان)": "شارع العليا الرياض المملكة العربيةالسعودية",
        "Address (Arabic)": "أنهار تكشارع الإمام عبدلله بن سعودحي الحمراءمدينة الرياضالمملكة العربية السعودية",
        "Other Details": text_list[-2:-1]
        }

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.endswith('.pdf'):
        try:
            image = convert_pdf_to_image(file.read())

            ocr_ar = PaddleOCR(use_gpu=False, lang="ar")
            ocr_en = PaddleOCR(use_gpu=False, lang="en")
            results_ar = ocr_ar.ocr(image, cls=True)
            results_en = ocr_en.ocr(image, cls=True)

            def extract_text(results):
                recognized_text = []
                for page_result in results:
                    for element in page_result:
                        text = element[1][0]
                        recognized_text.append(text)
                return recognized_text

            recognized_text_ar = extract_text(results_ar)
            recognized_text_en = extract_text(results_en)

            merged_results = recognized_text_ar + recognized_text_en
            print(merged_results)

            extracted_details = extract_invoice_details(merged_results)

            combined_results = {
                "extracted_details": extracted_details
            }

            return jsonify(combined_results), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Invalid file format. Only PDF files are supported."}), 400

if __name__ == '__main__':
    app.run(debug=True)