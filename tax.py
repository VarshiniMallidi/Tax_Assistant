import streamlit as st
import google.generativeai as genai
import pypdf
import json
import os
import requests
import re

try:
    API_KEY = ""  # Replace with your actual API key!
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
except ImportError:
    st.error("Error: google-generativeai library not found. Please install it using 'pip install google-generativeai'")
    st.stop()
except Exception as e:
    st.error(f"Error initializing Gemini model: {e}")
    st.stop()

if 'extracted_tax_data' not in st.session_state:
    st.session_state.extracted_tax_data = None
if 'json_file_path' not in st.session_state:
    st.session_state.json_file_path = None
if 'tax_calculated' not in st.session_state:
    st.session_state.tax_calculated = False
if 'calculation_results' not in st.session_state:
    st.session_state.calculation_results = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "edited_data" not in st.session_state:
    st.session_state.edited_data = False

SYSTEM_PROMPT = """
You are an expert in Indian taxation. Extract tax details from Form 16 PDFs.
Your task is to extract the following information and return it in a strict JSON format:
{
  {
  "salary_income": "numeric value",
  "interest_income": "numeric value",
  "rental_income": "numeric value",
  "digital_assets_income": "numeric value",
  "exempt_allowances": "numeric value",
  "home_loan_self": "numeric value",
  "home_loan_letout": "numeric value",
  "other_income": "numeric value",
  "deduction_80C": "numeric value",
  "deduction_80CCC": "numeric value",
  "deduction_80CCD1": "numeric value",
  "deduction_80CCD1B": "numeric value",
  "deduction_80CCD2": "numeric value",
  "deduction_80D": "numeric value",
  "deduction_80DD": "numeric value",
  "deduction_80DDB": "numeric value",
  "deduction_80E": "numeric value",
  "deduction_80EE": "numeric value",
  "deduction_80EEA": "numeric value",
  "deduction_80G": "numeric value",
  "deduction_80GG": "numeric value",
  "deduction_80GGA": "numeric value",
  "deduction_80GGC": "numeric value",
  "deduction_80TTA": "numeric value",
  "deduction_80TTB": "numeric value",
  "deduction_80U": "numeric value",
  "other_deductions": "numeric value",
  "gross_salary": "numeric value",
  "value_of_perquisites": "numeric value",
  "profits_in_lieu_of_salary": "numeric value",
  "allowances_exempt_under_section_10": "numeric value",
  "deductions_under_section_16": "numeric value",
  "income_chargeable_under_head_salaries": "numeric value",
  "income_from_house_property": "numeric value",
  "income_from_other_sources": "numeric value",
  "gross_total_income": "numeric value",
  "deductions_under_chapter_VI_A": "numeric value",
  "total_income": "numeric value",
  "tax_on_total_income": "numeric value",
  "rebate_under_section_87A": "numeric value",
  "surcharge": "numeric value",
  "health_and_education_cess": "numeric value",
  "relief_under_section_89": "numeric value",
  "net_tax_payable": "numeric value"
}

}
Replace 'numeric value' with the actual numbers found in the document. Use 0 for any fields not found.
Only return the JSON - no explanation or other text.
"""

def extract_text_from_pdf(uploaded_file):
    """Extracts text from a PDF file."""
    try:
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except pypdf.errors.PdfReadError as e:
        st.error(f"Error reading the PDF: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None


def extract_json_from_text(text):
    try:
        text = re.sub(r'\njson', '', text)
        text = re.sub(r'\n', '', text)
        json_pattern = re.search(r'\{.*\}', text, re.DOTALL)
        if json_pattern:
            json_text = json_pattern.group(0)
            return json.loads(json_text)
        return json.loads(text.strip())
    except (json.JSONDecodeError, AttributeError):
        st.error(f"Error parsing JSON: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None


def generate_itr1_json(extracted_data, calculation_results=None):
    """Generates an ITR-1 JSON file."""
    try:
        itr1_json = {
            "ITR1_FORM_DATA": {
                "Part_A_General_1": {
                    "AssesseeVerPAN": extracted_data.get("PAN", ""),
                    "FirstName": extracted_data.get("Name", ""),
                    "Address": extracted_data.get("Address", ""),
                    "MobileNo": extracted_data.get("Contact", "")
                },
                "Part_B_TI": {
                    "IncSalary": int(float(extracted_data.get("salary_income", 0))),
                    "IncInterest": int(float(extracted_data.get("interest_income", 0))),
                    "IncHouseProp": int(float(extracted_data.get("rental_income", 0))),
                    "IncOther": int(float(extracted_data.get("other_income", 0))),
                    "DigitalAssets": int(float(extracted_data.get("digital_assets_income", 0)))
                },
                "Part_C_Deductions": {
                    "Section80C": int(float(extracted_data.get("deduction_80C", 0))),
                    "Section80D": int(float(extracted_data.get("deduction_80D", 0))),
                    "Section80EEA": int(float(extracted_data.get("deduction_80EEA", 0))),
                    "Section80CCD2": int(float(extracted_data.get("deduction_80CCD2", 0))),
                    "Section80TTA": int(float(extracted_data.get("deduction_80TTA", 0))),
                    "Section80G": int(float(extracted_data.get("deduction_80G", 0))),
                    "Section80CCD": int(float(extracted_data.get("deduction_80CCD", 0))),
                    "OtherDeductions": int(float(extracted_data.get("other_deductions", 0)))
                },
                "ExemptAllowances": int(float(extracted_data.get("exempt_allowances", 0))),
                "HomeLoanInterestSelfOccupied": int(float(extracted_data.get("home_loan_self", 0))),
                "HomeLoanInterestLetOut": int(float(extracted_data.get("home_loan_letout", 0)))
            }
        }

        if calculation_results:
            itr1_json["Tax_Calculation"] = {
                "TotalIncome": calculation_results["total_income"],
                "TotalDeductions": calculation_results["total_deductions"],
                "TaxableIncomeOldRegime": calculation_results["taxable_income_old"],
                "TaxableIncomeNewRegime": calculation_results["taxable_income_new"],
                "TaxPayableOldRegime": calculation_results["tax_old"],
                "TaxPayableNewRegime": calculation_results["tax_new"],
                "RecommendedRegime": calculation_results["recommended_regime"]
            }

        json_filename = "itr1_prefilled.json"
        with open(json_filename, "w") as json_file:
            json.dump(itr1_json, json_file, indent=4)

        return json_filename
    except (TypeError, ValueError, KeyError) as e:
        st.error(f"Error generating ITR-1 JSON: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None
def edit_extracted_data():
    st.subheader("Edit Extracted Data")
    st.caption("Make necessary corrections to any incorrectly extracted values")
    
    if st.session_state.extracted_tax_data is not None:
        data = st.session_state.extracted_tax_data
        edited_data = {}
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("Income Details")
            edited_data["salary_income"] = st.number_input(
                "Income from Salary (₹)", 
                min_value=0, 
                value=int(float(data.get("salary_income", 0))),
                key="edit_salary_income"
            )
            
            edited_data["interest_income"] = st.number_input(
                "Income from Interest (₹)", 
                min_value=0, 
                value=int(float(data.get("interest_income", 0))),
                key="edit_interest_income"
            )
            
            edited_data["rental_income"] = st.number_input(
                "Rental Income (₹)", 
                min_value=0, 
                value=int(float(data.get("rental_income", 0))),
                key="edit_rental_income"
            )
            
            edited_data["digital_assets_income"] = st.number_input(
                "Income from Digital Assets (₹)", 
                min_value=0, 
                value=int(float(data.get("digital_assets_income", 0))),
                key="edit_digital_assets_income"
            )
            
            edited_data["exempt_allowances"] = st.number_input(
                "Exempt Allowances (₹)", 
                min_value=0, 
                value=int(float(data.get("exempt_allowances", 0))),
                key="edit_exempt_allowances"
            )
            
            edited_data["home_loan_self"] = st.number_input(
                "Interest on Home Loan - Self Occupied (₹)", 
                min_value=0, 
                value=int(float(data.get("home_loan_self", 0))),
                key="edit_home_loan_self"
            )
            
            edited_data["home_loan_letout"] = st.number_input(
                "Interest on Home Loan - Let Out (₹)", 
                min_value=0, 
                value=int(float(data.get("home_loan_letout", 0))),
                key="edit_home_loan_letout"
            )
            
            edited_data["other_income"] = st.number_input(
                "Other Income (₹)", 
                min_value=0, 
                value=int(float(data.get("other_income", 0))),
                key="edit_other_income"
            )
        
        with col2:
            st.write("Deduction Details")
            edited_data["deduction_80C"] = st.number_input(
                "Basic Deductions - 80C (₹)", 
                min_value=0, max_value=150000, 
                value=min(int(float(data.get("deduction_80C", 0))), 150000),
                key="edit_deduction_80C"
            )
            
            edited_data["deduction_80D"] = st.number_input(
                "Medical Insurance - 80D (₹)", 
                min_value=0, 
                value=int(float(data.get("deduction_80D", 0))),
                key="edit_deduction_80D"
            )
            
            edited_data["deduction_80EEA"] = st.number_input(
                "Interest on Housing Loan - 80EEA (₹)", 
                min_value=0, 
                value=int(float(data.get("deduction_80EEA", 0))),
                key="edit_deduction_80EEA"
            )
            
            edited_data["deduction_80CCD2"] = st.number_input(
                "Employer's NPS - 80CCD(2) (₹)", 
                min_value=0, 
                value=int(float(data.get("deduction_80CCD2", 0))),
                key="edit_deduction_80CCD2"
            )
            
            edited_data["deduction_80TTA"] = st.number_input(
                "Interest from Deposits - 80TTA (₹)", 
                min_value=0, max_value=10000, 
                value=min(int(float(data.get("deduction_80TTA", 0))), 10000),
                key="edit_deduction_80TTA"
            )
            
            edited_data["deduction_80G"] = st.number_input(
                "Donations to Charity - 80G (₹)", 
                min_value=0, 
                value=int(float(data.get("deduction_80G", 0))),
                key="edit_deduction_80G"
            )
            
            edited_data["deduction_80CCD"] = st.number_input(
                "Employee's NPS - 80CCD (₹)", 
                min_value=0, 
                value=int(float(data.get("deduction_80CCD", 0))),
                key="edit_deduction_80CCD"
            )
            
            edited_data["other_deductions"] = st.number_input(
                "Other Deductions (₹)", 
                min_value=0, 
                value=int(float(data.get("other_deductions", 0))),
                key="edit_other_deductions"
            )
        
        if "PAN" in data or "Name" in data or "Address" in data or "Contact" in data:
            st.write("Personal Information")
            col1, col2 = st.columns(2)
            
            with col1:
                edited_data["PAN"] = st.text_input(
                    "PAN Number",
                    value=data.get("PAN", ""),
                    key="edit_pan"
                )
                
                edited_data["Name"] = st.text_input(
                    "Full Name",
                    value=data.get("Name", ""),
                    key="edit_name"
                )
            
            with col2:
                edited_data["Address"] = st.text_area(
                    "Address",
                    value=data.get("Address", ""),
                    key="edit_address"
                )
                
                edited_data["Contact"] = st.text_input(
                    "Contact Number",
                    value=data.get("Contact", ""),
                    key="edit_contact"
                )

        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Save Changes", key="save_edited_data"):
                st.session_state.extracted_tax_data = edited_data

                json_file_path = generate_itr1_json(edited_data)
                st.session_state.json_file_path = json_file_path
                
                st.session_state.edited_data = False
                
                st.success("✅ Changes saved successfully!")
                st.rerun()
        
        with col2:
            if st.button("Cancel", key="cancel_edit"):
                st.session_state.edited_data = False
                st.rerun()



def form16_extraction():
    st.header("Upload Form 16 to Prefill Tax Calculator")

    uploaded_file = st.file_uploader("Upload Form 16 (PDF only)", type=["pdf"], key="form16_uploader_1")
    
    if uploaded_file is not None:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info("Click 'Extract Data' to process your Form 16")
        
        with col2:
            process_button = st.button("Extract Data", key="extract_data_button_1")
        
        if process_button:
            with st.spinner("Processing Form 16... This may take a moment"):
                extracted_text = extract_text_from_pdf(uploaded_file)
                
                try:
                    response = model.generate_content(SYSTEM_PROMPT + "\n\n" + extracted_text)
                    response_text = response.text if response else ""
                    
                    extracted_data = extract_json_from_text(response_text)
                    
                    if extracted_data:
                        st.session_state.extracted_tax_data = extracted_data
                        st.session_state.edited_data = False

                        json_file_path = generate_itr1_json(extracted_data)
                        st.session_state.json_file_path = json_file_path

                        st.session_state.tax_calculated = False
                        
                        st.success("✅ Data extracted successfully! Tax calculator has been prefilled.")
                        
                        with st.expander("View Extracted Data"):
                            st.json(extracted_data)

                        def enable_edit_mode():
                            st.session_state.edited_data = True
                            st.rerun()

                        st.button("Edit Extracted Data", key="edit_data_button", on_click=enable_edit_mode)
            
                    else:
                        st.error("Could not extract structured data. Please check the PDF format or try another file.")
                        st.code(response_text)

                        st.info("👉 Go to the 'Income Tax Calculator' tab to calculate your tax and then download your ITR-1 JSON file from the 'Download ITR-1 JSON' tab.")
                
                except Exception as e:
                    st.error(f"Error: {e}")
        if st.session_state.get("edited_data", False):
            edit_extracted_data()

def tax_calculator():
    st.header("Income Tax Calculator - India")

    financial_year = st.selectbox("Select Financial Year", ["2024-25", "2023-24"])
    age_group = st.radio("Select Age Group", ["Below 60", "60-80", "Above 80"])

    tax_data = st.session_state.extracted_tax_data or {}

    st.subheader("Income Details")
    col1, col2 = st.columns(2)
    
    with col1:
        salary_income = st.number_input(
            "Income from Salary (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("salary_income", 0)))
        )
        
        interest_income = st.number_input(
            "Income from Interest (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("interest_income", 0)))
        )
        
        rental_income = st.number_input(
            "Rental Income (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("rental_income", 0)))
        )
        
        digital_assets_income = st.number_input(
            "Income from Digital Assets (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("digital_assets_income", 0)))
        )
    
    with col2:
        exempt_allowances = st.number_input(
            "Exempt Allowances (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("exempt_allowances", 0)))
        )
        
        home_loan_self = st.number_input(
            "Interest on Home Loan - Self Occupied (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("home_loan_self", 0)))
        )
        
        home_loan_letout = st.number_input(
            "Interest on Home Loan - Let Out (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("home_loan_letout", 0)))
        )
        
        other_income = st.number_input(
            "Other Income (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("other_income", 0)))
        )

    st.subheader("Deductions")
    col1, col2 = st.columns(2)
    
    with col1:
        deduction_80C = st.number_input(
            "Basic Deductions - 80C (₹)", 
            min_value=0, max_value=150000, 
            value=min(int(float(tax_data.get("deduction_80C", 0))), 150000)
        )
        
        deduction_80D = st.number_input(
            "Medical Insurance - 80D (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("deduction_80D", 0)))
        )
        
        deduction_80EEA = st.number_input(
            "Interest on Housing Loan - 80EEA (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("deduction_80EEA", 0)))
        )
        
        deduction_80CCD2 = st.number_input(
            "Employer's NPS - 80CCD(2) (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("deduction_80CCD2", 0)))
        )
    
    with col2:
        deduction_80TTA = st.number_input(
            "Interest from Deposits - 80TTA (₹)", 
            min_value=0, max_value=10000, 
            value=min(int(float(tax_data.get("deduction_80TTA", 0))), 10000)
        )
        
        deduction_80G = st.number_input(
            "Donations to Charity - 80G (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("deduction_80G", 0)))
        )
        
        deduction_80CCD = st.number_input(
            "Employee's NPS - 80CCD (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("deduction_80CCD", 0)))
        )
        
        other_deductions = st.number_input(
            "Other Deductions (₹)", 
            min_value=0, 
            value=int(float(tax_data.get("other_deductions", 0)))
        )

    if st.button("Calculate Tax"):
        total_income = (salary_income + interest_income + rental_income + 
                        digital_assets_income + other_income)
        
        total_deductions = (deduction_80C + deduction_80D + deduction_80EEA + 
                            deduction_80CCD2 + deduction_80TTA + deduction_80G + 
                            deduction_80CCD + other_deductions)

        taxable_income_old = max(0, total_income - total_deductions)
        taxable_income_new = max(0, total_income - 50000) 

        tax_old = calculate_old_regime_tax(taxable_income_old, age_group)
        tax_new = calculate_new_regime_tax(taxable_income_new)

        recommended_regime = "New Regime" if tax_new < tax_old else "Old Regime"
        tax_saving = abs(tax_old - tax_new)

        calculation_results = {
            "total_income": total_income,
            "total_deductions": total_deductions,
            "taxable_income_old": taxable_income_old,
            "taxable_income_new": taxable_income_new,
            "tax_old": tax_old,
            "tax_new": tax_new,
            "recommended_regime": recommended_regime,
            "tax_saving": tax_saving,
            "age_group": age_group,
            "financial_year": financial_year
        }
        
        st.session_state.calculation_results = calculation_results
        st.session_state.tax_calculated = True

        st.subheader("Tax Calculation Results")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Income", f"₹{total_income:,}")
            st.metric("Total Deductions", f"₹{total_deductions:,}")
            st.metric("Taxable Income (Old Regime)", f"₹{taxable_income_old:,}")
            st.metric("Taxable Income (New Regime)", f"₹{taxable_income_new:,}")
        
        with col2:
            st.metric("Tax Payable (Old Regime)", f"₹{tax_old:,}")
            st.metric("Tax Payable (New Regime)", f"₹{tax_new:,}")
            st.metric("Tax Savings", f"₹{tax_saving:,}")
            st.success(f"Recommended: {recommended_regime} (Save ₹{tax_saving:,})")

        if st.session_state.extracted_tax_data:
            updated_data = st.session_state.extracted_tax_data.copy()

            updated_data["salary_income"] = salary_income
            updated_data["interest_income"] = interest_income
            updated_data["rental_income"] = rental_income
            updated_data["digital_assets_income"] = digital_assets_income
            updated_data["exempt_allowances"] = exempt_allowances
            updated_data["home_loan_self"] = home_loan_self
            updated_data["home_loan_letout"] = home_loan_letout
            updated_data["other_income"] = other_income

            updated_data["deduction_80C"] = deduction_80C
            updated_data["deduction_80D"] = deduction_80D
            updated_data["deduction_80EEA"] = deduction_80EEA
            updated_data["deduction_80CCD2"] = deduction_80CCD2
            updated_data["deduction_80TTA"] = deduction_80TTA
            updated_data["deduction_80G"] = deduction_80G
            updated_data["deduction_80CCD"] = deduction_80CCD
            updated_data["other_deductions"] = other_deductions
            
            st.session_state.extracted_tax_data = updated_data
            json_file_path = generate_itr1_json(updated_data, calculation_results)
            st.session_state.json_file_path = json_file_path

            st.info("✅ Tax calculations complete! You can now download your ITR-1 JSON file from the 'Download ITR-1 JSON' tab.")

def calculate_old_regime_tax(income, age_group):

    tax = 0
    
    if age_group == "Below 60":
        if income <= 250000:
            tax = 0
        elif income <= 500000:
            tax = (income - 250000) * 0.05
        elif income <= 1000000:
            tax = 12500 + (income - 500000) * 0.20
        else:
            tax = 112500 + (income - 1000000) * 0.30
    
    elif age_group == "60-80":
        if income <= 300000:
            tax = 0
        elif income <= 500000:
            tax = (income - 300000) * 0.05
        elif income <= 1000000:
            tax = 10000 + (income - 500000) * 0.20
        else:
            tax = 110000 + (income - 1000000) * 0.30
    
    else:  
        if income <= 500000:
            tax = 0
        elif income <= 1000000:
            tax = (income - 500000) * 0.20
        else:
            tax = 100000 + (income - 1000000) * 0.30
    
    tax += tax * 0.04
    
    return round(tax)

def calculate_new_regime_tax(income):
    tax = 0
    
    if income <= 300000:
        tax = 0
    elif income <= 600000:
        tax = (income - 300000) * 0.05
    elif income <= 900000:
        tax = 15000 + (income - 600000) * 0.10
    elif income <= 1200000:
        tax = 45000 + (income - 900000) * 0.15
    elif income <= 1500000:
        tax = 90000 + (income - 1200000) * 0.20
    else:
        tax = 150000 + (income - 1500000) * 0.30

    tax += tax * 0.04
    
    return round(tax)

def tax_advisor_chatbot():
    st.header("AI Tax Advisor")

    if "messages" not in st.session_state:
        st.session_state.messages = []
  
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_input = st.chat_input("Ask about Indian taxes, deductions, or ITR filing:")
    
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                tax_prompt = "You are an expert Indian tax advisor. Answer the following tax-related question thoroughly and accurately: " + user_input
                response = model.generate_content(tax_prompt)

                st.write(response.text)

                st.session_state.messages.append({"role": "assistant", "content": response.text})

def download_json_tab():
    st.header("Download ITR-1 JSON File")
    
    if not st.session_state.extracted_tax_data:
        st.warning("No tax data available. Please upload your Form 16 in the 'Upload Form 16' tab first.")
        return
    
    if not st.session_state.tax_calculated:
        st.warning("Please calculate your tax in the 'Income Tax Calculator' tab before downloading the JSON file.")
        return
    
    if st.session_state.json_file_path and os.path.exists(st.session_state.json_file_path):
        st.success("Your ITR-1 JSON file is ready for download!")
        
        if st.session_state.calculation_results:
            results = st.session_state.calculation_results

            st.subheader("Tax Calculation Summary")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Financial Year", results["financial_year"])
                st.metric("Age Group", results["age_group"])
                st.metric("Total Income", f"₹{results['total_income']:,}")
                st.metric("Total Deductions", f"₹{results['total_deductions']:,}")
            
            with col2:
                st.metric("Tax (Old Regime)", f"₹{results['tax_old']:,}")
                st.metric("Tax (New Regime)", f"₹{results['tax_new']:,}")
                recommended = results["recommended_regime"]
                savings = results["tax_saving"]
                st.metric("Recommended Regime", f"{recommended} (Save ₹{savings:,})")

        st.info("""
        ## How to use this file:
        
        1. Download the ITR-1 JSON file by clicking the button below
        2. Go to the Income Tax Portal (https://www.incometax.gov.in/)
        3. Login with your credentials
        4. Navigate to "e-File" > "Income Tax Return"
        5. Choose "Upload JSON" option
        6. Select the downloaded file
        7. Review the prefilled information and make necessary adjustments
        8. Complete and submit your ITR
        """)
        
        with open(st.session_state.json_file_path, "rb") as f:
            st.download_button(
                label="📥 Download ITR-1 JSON File",
                data=f,
                file_name="itr1_prefilled.json",
                mime="application/json",
                key="download_tab_button"
            )
    else:
        st.error("An error occurred with the JSON file. Please try calculating your tax again.")

def home():
    st.title("🚀 AI-Powered Tax Filing Co-Pilot")
    st.subheader("Upload Form 16 & get tax details automatically!")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📑 Upload Form 16", 
        "💰 Income Tax Calculator", 
        "💬 Tax Advisor", 
        "📥 Download ITR-1 JSON"
    ])
    
    with tab1:
        form16_extraction()
    
    with tab2:
        tax_calculator()
    
    with tab3:
        tax_advisor_chatbot()
    
    with tab4:
        download_json_tab()

if __name__ == "__main__":
    home()
