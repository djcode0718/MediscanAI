import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend import embeddings
import numpy as np

def test_embeddings_vector():
    text = ['headache and nausea', 'i have skin allergy. at a ted 2000 FOR THERAPE USE Lic. No. in Ltd. 0S8 NDIA ead. Trade Mark Compesition Eachsugar- lablet contains: 10.0 mg Thiamine Me aleIP 0.0n Tablets otlamin B-Com Ribolimin te Nicotinic Ao 75.0 Niecinamide 3.0 m T5H ha ad 100.0 BIOWAT 260 VitarnyC.IP BOWUSP 260.0 8 Light Magne oxide IP BEPLEX FORTE Equivalent o al Magnesium 32.4 "To report produ ind ar Adverse Drug Anglo-French Drug reaction dial Toll P0-209-2505 compensa Morage dustriesLimited or email al dsrm Store proke Pp(No.4.Phase Industrial Area Compos Eachsugal ablelcontains: BEP Tablets Thiamine Mo 0.0T ablets ofamin B-Com Riboflayy Ip 25.0.m Nicotinic 75.0m9 Niacinamio oride IP 3.0 mg With Vitar Cand Pynido Calclum Pan taIp 0.mo Risrin26 Cyanoc - BEPLE FORTE Equrealent to al Magnesium 32.4 mg GE Eint or Adverse Drug Colder: Car Manufactured In India "To report produ Appropriate ov of Vitamins added to aglo-Frenich Drug reaction dial Toll ir 800-209-2505 ndustries Limited compensate los or email al ds Store protec light and moisture Pot No 4. Phase Industrial Area, at a tempera er-xceeding 25°C. Dosage: As by the Physician Kaina Soton E FOR THER CUSE 2000 Rogd. Trade ANOIA 10.0 1 lauleis o 25.0 mo Nicot Niacinarnide 75 0 Pynidoxine loride IP Calcium Par 3AJ0 5.0mg Folic Acid IP 1.5m9 Cyanocoba 15.01 11 Vitamin C.J 100.0 Biollin USP 260.0 FORTE']
    print(f"\n[DEBUG] Input text(s): {text}")

    vectors = embeddings.embed_texts(text)

    # Debug info
    print(f"[DEBUG] Returned type: {type(vectors)}")
    print(f"[DEBUG] Length of returned list: {len(vectors)}")

    # Each vector should be a NumPy array
    for i, vec in enumerate(vectors):
        print(f"[DEBUG] Vector {i} type: {type(vec)}")
        print(f"[DEBUG] Vector {i} shape: {vec.shape}")
        print(f"[DEBUG] First 5 values of vector {i}: {vec[:5]}")

        # Assertions
        assert isinstance(vec, np.ndarray), "Each embedding should be a numpy array"
        assert vec.shape[0] > 0, "Embedding vector should not be empty"

    # Extra check: embedding dimension consistency
    dims = [vec.shape[0] for vec in vectors]
    assert all(d == dims[0] for d in dims), "All embeddings should have the same dimension"
    print(f"[DEBUG] Embedding dimension: {dims[0]}")

if __name__ == "__main__":
    test_embeddings_vector()
