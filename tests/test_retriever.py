# # test/test_retriever.py
# import sys, os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# from backend.retriever import MultiRetriever

# def test_retriever():
#     # query = "i have cold and cough, i am using paracetamol"
#     query = 'i have skin allergy. at a ted 2000 FOR THERAPE USE Lic. No. in Ltd. 0S8 NDIA ead. Trade Mark Compesition Eachsugar- lablet contains: 10.0 mg Thiamine Me aleIP 0.0n Tablets otlamin B-Com Ribolimin te Nicotinic Ao 75.0 Niecinamide 3.0 m T5H ha ad 100.0 BIOWAT 260 VitarnyC.IP BOWUSP 260.0 8 Light Magne oxide IP BEPLEX FORTE Equivalent o al Magnesium 32.4 "To report produ ind ar Adverse Drug Anglo-French Drug reaction dial Toll P0-209-2505 compensa Morage dustriesLimited or email al dsrm Store proke Pp(No.4.Phase Industrial Area Compos Eachsugal ablelcontains: BEP Tablets Thiamine Mo 0.0T ablets ofamin B-Com Riboflayy Ip 25.0.m Nicotinic 75.0m9 Niacinamio oride IP 3.0 mg With Vitar Cand Pynido Calclum Pan taIp 0.mo Risrin26 Cyanoc - BEPLE FORTE Equrealent to al Magnesium 32.4 mg GE Eint or Adverse Drug Colder: Car Manufactured In India "To report produ Appropriate ov of Vitamins added to aglo-Frenich Drug reaction dial Toll ir 800-209-2505 ndustries Limited compensate los or email al ds Store protec light and moisture Pot No 4. Phase Industrial Area, at a tempera er-xceeding 25°C. Dosage: As by the Physician Kaina Soton E FOR THER CUSE 2000 Rogd. Trade ANOIA 10.0 1 lauleis o 25.0 mo Nicot Niacinarnide 75 0 Pynidoxine loride IP Calcium Par 3AJ0 5.0mg Folic Acid IP 1.5m9 Cyanocoba 15.01 11 Vitamin C.J 100.0 Biollin USP 260.0 FORTE'
#     print(f"\n[TEST] Running retriever on query: '{query}'\n")

#     retriever = MultiRetriever()  # loads FAISS indexes + jsonl mappings

#     # Run search across all indexes
#     results = retriever.search_all(query, top_k=5)

#     for index_name, res_list in results.items():
#         print(f"\n--- Results from index: {index_name} ---")
#         if not res_list:
#             print("No results found.")
#         for rank, (key, score, obj) in enumerate(res_list, 1):
#             snippet = str(obj)[:200]  # show first 200 chars of record
#             print(f"{rank}. Key={key} | Score={score:.4f} | Record={snippet}")

# if __name__ == "__main__":
#     test_retriever()


import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.retriever import MultiRetriever

def print_results(results_list, index_name):
    print(f"\n--- Results from index: {index_name} ---")
    if not results_list:
        print("No results found.")
    for rank, (key, score, obj) in enumerate(results_list, 1):
        snippet = str(obj)[:200]
        print(f"{rank}. Key={key} | Score={score:.4f} | Record={snippet}")

def test_retriever():
    user_text = 'I’ve been coughing for about a week now. It started with a sore throat, then turned into a dry cough. The last two days I’ve had mild fever in the evenings. I tried paracetamol and ginger tea, which helped a bit, but the cough still comes back. I think it started after I got drenched in the rain.'
    ocr_text = 'at a ted 2000 FOR THERAPE USE Lic. No. in Ltd. 0S8 NDIA ead. Trade Mark Compesition Eachsugar- lablet contains: 10.0 mg Thiamine Me aleIP 0.0n Tablets otlamin B-Com Ribolimin te Nicotinic Ao 75.0 Niecinamide 3.0 m T5H ha ad 100.0 BIOWAT 260 VitarnyC.IP BOWUSP 260.0 8 Light Magne oxide IP BEPLEX FORTE Equivalent o al Magnesium 32.4 "To report produ ind ar Adverse Drug Anglo-French Drug reaction dial Toll P0-209-2505 compensa Morage dustriesLimited or email al dsrm Store proke Pp(No.4.Phase Industrial Area Compos Eachsugal ablelcontains: BEP Tablets Thiamine Mo 0.0T ablets ofamin B-Com Riboflayy Ip 25.0.m Nicotinic 75.0m9 Niacinamio oride IP 3.0 mg With Vitar Cand Pynido Calclum Pan taIp 0.mo Risrin26 Cyanoc - BEPLE FORTE Equrealent to al Magnesium 32.4 mg GE Eint or Adverse Drug Colder: Car Manufactured In India "To report produ Appropriate ov of Vitamins added to aglo-Frenich Drug reaction dial Toll ir 800-209-2505 ndustries Limited compensate los or email al ds Store protec light and moisture Pot No 4. Phase Industrial Area, at a tempera er-xceeding 25°C. Dosage: As by the Physician Kaina Soton E FOR THER CUSE 2000 Rogd. Trade ANOIA 10.0 1 lauleis o 25.0 mo Nicot Niacinarnide 75 0 Pynidoxine loride IP Calcium Par 3AJ0 5.0mg Folic Acid IP 1.5m9 Cyanocoba 15.01 11 Vitamin C.J 100.0 Biollin USP 260.0 FORTE'
    
    retriever = MultiRetriever()

    print("\n" + "="*50)
    print("      Part 1: Retrievals for User Text")
    print(f"      Query: '{user_text}'")
    print("="*50)
    
    user_indexes_to_search = ["diseases", "drugs"]
    for index_name in user_indexes_to_search:
        results = retriever.search_specific(index_name, user_text, top_k=5)
        print_results(results, index_name)

    print("\n\n" + "="*50)
    print("       Part 2: Retrievals for OCR Text")
    print(f"       Query: '{ocr_text[:60]}...'")
    print("="*50)
    
    ocr_indexes_to_search = ["drug_dict", "drugs"]
    for index_name in ocr_indexes_to_search:
        results = retriever.search_specific(index_name, ocr_text, top_k=5)
        print_results(results, index_name)

if __name__ == "__main__":
    test_retriever()