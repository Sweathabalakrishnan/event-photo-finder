# import os
# import json
# import math
# from typing import List, Dict
# from fastapi import FastAPI, Form
# from deepface import DeepFace
# from PIL import Image

# app = FastAPI()

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# EMBEDDINGS_DIR = os.path.join(BASE_DIR, "embeddings")
# CROPS_DIR = os.path.join(BASE_DIR, "face_crops")
# REF_CROPS_DIR = os.path.join(BASE_DIR, "reference_crops")

# os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
# os.makedirs(CROPS_DIR, exist_ok=True)
# os.makedirs(REF_CROPS_DIR, exist_ok=True)

# DETECTOR_BACKEND = "retinaface"
# MIN_FACE_SIZE = 16

# MODELS = {
#     "ArcFace": {
#         "weight": 0.75,
#         "threshold": 0.62
#     },
#     "Facenet512": {
#         "weight": 0.25,
#         "threshold": 0.50
#     }
# }

# # clustering threshold on ArcFace score
# CLUSTER_ARC_THRESHOLD = 0.38


# # -----------------------------------
# # PATH HELPERS
# # -----------------------------------
# def event_embeddings_path(event_code: str) -> str:
#     return os.path.join(EMBEDDINGS_DIR, f"{event_code}.json")


# def event_crop_dir(event_code: str) -> str:
#     path = os.path.join(CROPS_DIR, event_code)
#     os.makedirs(path, exist_ok=True)
#     return path


# # -----------------------------------
# # LOAD / SAVE
# # -----------------------------------
# def load_event_embeddings(event_code: str):
#     path = event_embeddings_path(event_code)
#     if not os.path.exists(path):
#         print(f"[INFO] No embeddings file found for event: {event_code}")
#         return []
#     with open(path, "r", encoding="utf-8") as f:
#         return json.load(f)


# def save_event_embeddings(event_code: str, data):
#     path = event_embeddings_path(event_code)
#     with open(path, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=2)


# # -----------------------------------
# # MATH
# # -----------------------------------
# def l2_normalize(vec):
#     norm = math.sqrt(sum(v * v for v in vec))
#     if norm == 0:
#         return vec
#     return [v / norm for v in vec]


# def average_embeddings(embeddings):
#     if not embeddings:
#         return None
#     dim = len(embeddings[0])
#     avg = [0.0] * dim
#     for emb in embeddings:
#         for i in range(dim):
#             avg[i] += emb[i]
#     avg = [v / len(embeddings) for v in avg]
#     return l2_normalize(avg)


# def cosine_distance(vec1, vec2):
#     dot = sum(a * b for a, b in zip(vec1, vec2))
#     norm1 = math.sqrt(sum(a * a for a in vec1))
#     norm2 = math.sqrt(sum(b * b for b in vec2))
#     if norm1 == 0 or norm2 == 0:
#         return 1.0
#     similarity = dot / (norm1 * norm2)
#     return 1.0 - similarity


# def score_to_confidence(score: float) -> float:
#     """
#     Lower score = higher confidence.
#     Maps typical match score range to 0-100.
#     """
#     conf = 100.0 * (1.0 - min(max((score - 0.05) / 0.65, 0.0), 1.0))
#     return round(conf, 2)


# # -----------------------------------
# # FACE / EMBEDDING HELPERS
# # -----------------------------------
# def detect_faces(image_path: str):
#     try:
#         return DeepFace.extract_faces(
#             img_path=image_path,
#             detector_backend=DETECTOR_BACKEND,
#             enforce_detection=False,
#             align=True
#         )
#     except Exception as e:
#         print(f"[FACE DETECT ERROR] {image_path} -> {str(e)}")
#         return []


# def get_embedding_from_crop(image_path: str, model_name: str):
#     try:
#         reps = DeepFace.represent(
#             img_path=image_path,
#             model_name=model_name,
#             detector_backend="skip",
#             enforce_detection=False,
#             align=True
#         )
#         if not reps:
#             print(f"[WARN] No embedding for crop: {image_path} | model={model_name}")
#             return None
#         return l2_normalize(reps[0]["embedding"])
#     except Exception as e:
#         print(f"[EMBEDDING ERROR] {image_path} | model={model_name} -> {str(e)}")
#         return None


# def get_embeddings_for_crop(image_path: str) -> Dict[str, List[float]]:
#     result = {}
#     for model_name in MODELS.keys():
#         emb = get_embedding_from_crop(image_path, model_name)
#         if emb is not None:
#             result[model_name] = emb
#     return result


# def save_largest_reference_crop(image_path: str, out_dir: str):
#     faces = detect_faces(image_path)
#     print("[REFERENCE FACES DETECTED]", len(faces))

#     if len(faces) == 0:
#         return None, 0

#     try:
#         image = Image.open(image_path).convert("RGB")
#     except Exception as e:
#         print("[REFERENCE IMAGE OPEN ERROR]", str(e))
#         return None, 0

#     best_face = None
#     best_area = 0

#     for idx, face in enumerate(faces):
#         area = face.get("facial_area", {})
#         x = int(area.get("x", 0))
#         y = int(area.get("y", 0))
#         w = int(area.get("w", 0))
#         h = int(area.get("h", 0))
#         face_area = w * h

#         print(f"[REFERENCE FACE {idx}] x={x}, y={y}, w={w}, h={h}, area={face_area}")

#         if face_area > best_area:
#             best_area = face_area
#             best_face = (x, y, w, h)

#     if best_face is None:
#         return None, 0

#     x, y, w, h = best_face
#     crop = image.crop((x, y, x + w, y + h))

#     base = os.path.basename(image_path)
#     crop_name = f"ref_{os.path.splitext(base)[0]}.jpg"
#     crop_path = os.path.join(out_dir, crop_name)
#     crop.save(crop_path)

#     print("[REFERENCE CROP SAVED]", crop_name)
#     return crop_path, best_area


# # -----------------------------------
# # CLUSTERING
# # -----------------------------------
# def assign_clusters(records):
#     """
#     Auto-cluster indexed faces per event using ArcFace score.
#     This groups likely same-person faces across different photos.
#     """
#     clusters = []

#     for idx, record in enumerate(records):
#         arc_emb = record.get("embeddings", {}).get("ArcFace")
#         if not arc_emb:
#             record["cluster_id"] = None
#             continue

#         best_cluster = None
#         best_score = 999

#         for cluster in clusters:
#             cluster_arc = cluster["arc_centroid"]
#             arc_score = cosine_distance(arc_emb, cluster_arc)

#             if arc_score < best_score:
#                 best_score = arc_score
#                 best_cluster = cluster

#         if best_cluster is not None and best_score <= CLUSTER_ARC_THRESHOLD:
#             record["cluster_id"] = best_cluster["cluster_id"]
#             best_cluster["members"].append(record)
#             member_embs = [
#                 m["embeddings"]["ArcFace"]
#                 for m in best_cluster["members"]
#                 if "ArcFace" in m.get("embeddings", {})
#             ]
#             best_cluster["arc_centroid"] = average_embeddings(member_embs)
#         else:
#             cluster_id = f"person_{len(clusters) + 1}"
#             record["cluster_id"] = cluster_id
#             clusters.append({
#                 "cluster_id": cluster_id,
#                 "members": [record],
#                 "arc_centroid": arc_emb
#             })

#     return records, clusters


# # -----------------------------------
# # ROOT
# # -----------------------------------
# @app.get("/")
# def root():
#     return {"message": "AI service running"}


# # -----------------------------------
# # INDEX EVENT PHOTO
# # -----------------------------------
# @app.post("/index-photo")
# def index_photo(event_code: str = Form(...), photo_path: str = Form(...)):
#     print("\n==================================================")
#     print("INDEXING EVENT PHOTO")
#     print("==================================================")
#     print("[EVENT CODE]", event_code)
#     print("[PHOTO PATH ]", photo_path)

#     try:
#         if not os.path.exists(photo_path):
#             print("[ERROR] Photo path does not exist")
#             return {
#                 "filename": os.path.basename(photo_path),
#                 "faces_indexed": 0,
#                 "error": "Photo path does not exist"
#             }

#         records = load_event_embeddings(event_code)
#         crop_dir = event_crop_dir(event_code)
#         filename = os.path.basename(photo_path)

#         records = [r for r in records if r["filename"] != filename]

#         faces = detect_faces(photo_path)
#         print("[FACES DETECTED]", len(faces))

#         try:
#             image = Image.open(photo_path).convert("RGB")
#         except Exception as e:
#             print("[IMAGE OPEN ERROR]", str(e))
#             return {
#                 "filename": filename,
#                 "faces_indexed": 0,
#                 "error": f"Unable to open image: {str(e)}"
#             }

#         face_records = []

#         for idx, face in enumerate(faces):
#             try:
#                 area = face.get("facial_area", {})
#                 x = int(area.get("x", 0))
#                 y = int(area.get("y", 0))
#                 w = int(area.get("w", 0))
#                 h = int(area.get("h", 0))
#                 face_area = w * h

#                 print(f"\n[FACE {idx}] x={x}, y={y}, w={w}, h={h}, area={face_area}")

#                 if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
#                     print(f"[SKIP FACE {idx}] Too small for indexing (MIN_FACE_SIZE={MIN_FACE_SIZE})")
#                     continue

#                 crop = image.crop((x, y, x + w, y + h))
#                 crop_filename = f"{os.path.splitext(filename)[0]}_face_{idx}.jpg"
#                 crop_path = os.path.join(crop_dir, crop_filename)
#                 crop.save(crop_path)

#                 embeddings = get_embeddings_for_crop(crop_path)
#                 if not embeddings:
#                     print(f"[SKIP FACE {idx}] No embeddings created")
#                     continue

#                 print(f"[INDEX FACE {idx}] success | crop={crop_filename} | models={list(embeddings.keys())}")

#                 face_records.append({
#                     "filename": filename,
#                     "crop_filename": crop_filename,
#                     "crop_path": crop_path,
#                     "embeddings": embeddings,
#                     "face_area": face_area
#                 })

#             except Exception as e:
#                 print(f"[FACE {idx} PROCESS ERROR] {str(e)}")
#                 continue

#         records.extend(face_records)

#         # auto-cluster all indexed faces after every indexing call
#         records, clusters = assign_clusters(records)
#         save_event_embeddings(event_code, records)

#         print(f"[DONE] Faces indexed: {len(face_records)}")
#         print(f"[CLUSTERS] Total clusters now: {len(clusters)}")

#         return {
#             "filename": filename,
#             "faces_indexed": len(face_records),
#             "clusters_total": len(clusters)
#         }

#     except Exception as e:
#         print("[INDEX ROUTE ERROR]", str(e))
#         return {
#             "filename": os.path.basename(photo_path),
#             "faces_indexed": 0,
#             "error": str(e)
#         }


# # -----------------------------------
# # MATCH SELFIES
# # -----------------------------------
# @app.post("/match-selfie")
# def match_selfie(event_code: str = Form(...), selfie_paths: List[str] = Form(...)):
#     print("\n==================================================")
#     print("MATCHING STARTED")
#     print("==================================================")
#     print("[EVENT CODE  ]", event_code)
#     print("[SELFIE PATHS]", selfie_paths)

#     try:
#         records = load_event_embeddings(event_code)
#         if not records:
#             print("[WARN] No indexed faces found for this event")
#             return {"matches": [], "count": 0, "ranked_matches": []}

#         # ensure clusters are present even for old data
#         records, clusters = assign_clusters(records)
#         save_event_embeddings(event_code, records)

#         print("[INDEXED FACE RECORDS FOUND]", len(records))
#         print("[CLUSTERS FOUND]", len(clusters))

#         reference_embeddings_by_model: Dict[str, List[List[float]]] = {m: [] for m in MODELS.keys()}

#         for i, selfie_path in enumerate(selfie_paths):
#             print(f"\n----------------------------------")
#             print(f"REFERENCE PHOTO {i + 1}")
#             print(f"----------------------------------")
#             print("[PATH]", selfie_path)

#             if not os.path.exists(selfie_path):
#                 print("[WARN] File does not exist")
#                 continue

#             crop_path, crop_area = save_largest_reference_crop(selfie_path, REF_CROPS_DIR)
#             if crop_path is None:
#                 print("[WARN] Could not create reference crop")
#                 continue

#             ref_embeddings = get_embeddings_for_crop(crop_path)
#             if ref_embeddings:
#                 for model_name, emb in ref_embeddings.items():
#                     reference_embeddings_by_model[model_name].append(emb)
#                 print("[OK] Reference embeddings created | crop area =", crop_area)

#         if len(reference_embeddings_by_model["ArcFace"]) < 2 or len(reference_embeddings_by_model["Facenet512"]) < 2:
#             print("[ERROR] Need at least 2 valid references for both ArcFace and Facenet512")
#             return {"matches": [], "count": 0, "ranked_matches": []}

#         centroid_by_model = {
#             model_name: average_embeddings(embs)
#             for model_name, embs in reference_embeddings_by_model.items()
#         }

#         print("\n[REFERENCE CENTROIDS READY]")
#         for model_name in MODELS.keys():
#             print(f" - {model_name}: {len(reference_embeddings_by_model[model_name])} refs")

#         scored = []

#         print("\n==================================================")
#         print("COMPARING INDEXED FACES")
#         print("==================================================")

#         for record in records:
#             try:
#                 if "embeddings" not in record:
#                     continue

#                 model_distances = {}
#                 weighted_score = 0.0
#                 total_weight = 0.0
#                 valid = True

#                 for model_name, model_cfg in MODELS.items():
#                     face_emb = record["embeddings"].get(model_name)
#                     if face_emb is None:
#                         valid = False
#                         break

#                     centroid_dist = cosine_distance(centroid_by_model[model_name], face_emb)
#                     ref_dists = [
#                         cosine_distance(ref_emb, face_emb)
#                         for ref_emb in reference_embeddings_by_model[model_name]
#                     ]
#                     min_ref_dist = min(ref_dists)

#                     model_score = (0.65 * centroid_dist) + (0.35 * min_ref_dist)

#                     model_distances[model_name] = {
#                         "centroid": centroid_dist,
#                         "min_ref": min_ref_dist,
#                         "score": model_score
#                     }

#                     weighted_score += model_score * model_cfg["weight"]
#                     total_weight += model_cfg["weight"]

#                 if total_weight == 0 or not valid:
#                     continue

#                 arc_score = model_distances["ArcFace"]["score"]
#                 facenet_score = model_distances["Facenet512"]["score"]

#                 model_pass = (
#                     (arc_score <= 0.62 and facenet_score <= 0.50)
#                     or
#                     (arc_score <= 0.52 and facenet_score <= 0.58)
#                 )

#                 final_score = weighted_score / total_weight

#                 face_area = record.get("face_area", 0)
#                 if face_area < 500:
#                     final_score += 0.04
#                 elif face_area < 1000:
#                     final_score += 0.02

#                 confidence = score_to_confidence(final_score)

#                 print(
#                     "[COMPARE]",
#                     "photo =", record["filename"],
#                     "| crop =", record["crop_filename"],
#                     "| cluster =", record.get("cluster_id"),
#                     "| arc =", round(arc_score, 6),
#                     "| facenet =", round(facenet_score, 6),
#                     "| area =", face_area,
#                     "| final =", round(final_score, 6),
#                     "| confidence =", confidence,
#                     "| pass =", model_pass
#                 )

#                 scored.append({
#                     "filename": record["filename"],
#                     "crop_filename": record["crop_filename"],
#                     "cluster_id": record.get("cluster_id"),
#                     "score": final_score,
#                     "confidence": confidence,
#                     "face_area": face_area,
#                     "model_pass": model_pass,
#                     "arc_score": arc_score,
#                     "facenet_score": facenet_score
#                 })

#             except Exception as e:
#                 print("[COMPARE ERROR]", str(e))
#                 continue

#         if not scored:
#             print("[WARN] No scored entries found")
#             return {"matches": [], "count": 0, "ranked_matches": []}

#         passed = [x for x in scored if x["model_pass"]]
#         if not passed:
#             print("[WARN] No entries passed model rules")
#             return {"matches": [], "count": 0, "ranked_matches": []}

#         passed.sort(key=lambda x: x["score"])
#         best_score = passed[0]["score"]

#         threshold = max(0.58, min(best_score + 0.16, 0.68))

#         print("\n[BEST SCORE]", round(best_score, 6))
#         print("[THRESHOLD ]", round(threshold, 6))

#         filtered = [x for x in passed if x["score"] <= threshold]
#         print("[ENTRIES WITHIN THRESHOLD]", len(filtered))

#         # keep best face per original photo
#         best_per_photo = {}
#         for item in filtered:
#             filename = item["filename"]
#             if filename not in best_per_photo or item["score"] < best_per_photo[filename]["score"]:
#                 best_per_photo[filename] = item

#         final_items = sorted(best_per_photo.values(), key=lambda x: x["score"])
#         final = [item["filename"] for item in final_items]

#         print("\n==================================================")
#         print("FINAL MATCHES")
#         print("==================================================")
#         for item in final_items:
#             print(
#                 "photo =", item["filename"],
#                 "| cluster =", item["cluster_id"],
#                 "| final =", round(item["score"], 6),
#                 "| confidence =", item["confidence"],
#                 "| arc =", round(item["arc_score"], 6),
#                 "| facenet =", round(item["facenet_score"], 6),
#                 "| area =", item["face_area"]
#             )

#         print("[TOTAL FINAL MATCHES]", len(final))

#         return {
#             "matches": final,
#             "count": len(final),
#             "ranked_matches": final_items
#         }

#     except Exception as e:
#         print("[MATCH ROUTE ERROR]", str(e))
#         return {
#             "matches": [],
#             "count": 0,
#             "ranked_matches": [],
#             "error": str(e)
#         }


# # -----------------------------------
# # OPTIONAL: CLUSTER SUMMARY
# # -----------------------------------
# @app.get("/cluster-summary/{event_code}")
# def cluster_summary(event_code: str):
#     records = load_event_embeddings(event_code)
#     if not records:
#         return {"event_code": event_code, "clusters": []}

#     records, clusters = assign_clusters(records)
#     save_event_embeddings(event_code, records)

#     summary = []
#     for c in clusters:
#       summary.append({
#           "cluster_id": c["cluster_id"],
#           "count": len(c["members"]),
#           "photos": sorted(list(set([m["filename"] for m in c["members"]])))
#       })

#     return {
#         "event_code": event_code,
#         "clusters": summary}



import os
import json
import math
from typing import List, Dict
from fastapi import FastAPI, Form, UploadFile, File
from deepface import DeepFace
from PIL import Image

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMBEDDINGS_DIR = os.path.join(BASE_DIR, "embeddings")
CROPS_DIR = os.path.join(BASE_DIR, "face_crops")
REF_CROPS_DIR = os.path.join(BASE_DIR, "reference_crops")
TEMP_DIR = os.path.join(BASE_DIR, "temp_uploads")

os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
os.makedirs(CROPS_DIR, exist_ok=True)
os.makedirs(REF_CROPS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

DETECTOR_BACKEND = "retinaface"
MIN_FACE_SIZE = 16

MODELS = {
    "ArcFace": {
        "weight": 0.75,
        "threshold": 0.62
    },
    "Facenet512": {
        "weight": 0.25,
        "threshold": 0.50
    }
}

CLUSTER_ARC_THRESHOLD = 0.38


# -----------------------------------
# PATH HELPERS
# -----------------------------------
def event_embeddings_path(event_code: str) -> str:
    return os.path.join(EMBEDDINGS_DIR, f"{event_code}.json")


def event_crop_dir(event_code: str) -> str:
    path = os.path.join(CROPS_DIR, event_code)
    os.makedirs(path, exist_ok=True)
    return path


def save_upload_to_temp(upload_file: UploadFile, prefix: str = "") -> str:
    safe_name = os.path.basename(upload_file.filename or "upload.jpg")
    filename = f"{prefix}{safe_name}"
    temp_path = os.path.join(TEMP_DIR, filename)

    with open(temp_path, "wb") as f:
        f.write(upload_file.file.read())

    return temp_path


def cleanup_file(file_path: str):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"[CLEANUP ERROR] {file_path} -> {str(e)}")


# -----------------------------------
# LOAD / SAVE
# -----------------------------------
def load_event_embeddings(event_code: str):
    path = event_embeddings_path(event_code)
    if not os.path.exists(path):
        print(f"[INFO] No embeddings file found for event: {event_code}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_event_embeddings(event_code: str, data):
    path = event_embeddings_path(event_code)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# -----------------------------------
# MATH
# -----------------------------------
def l2_normalize(vec):
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def average_embeddings(embeddings):
    if not embeddings:
        return None
    dim = len(embeddings[0])
    avg = [0.0] * dim
    for emb in embeddings:
        for i in range(dim):
            avg[i] += emb[i]
    avg = [v / len(embeddings) for v in avg]
    return l2_normalize(avg)


def cosine_distance(vec1, vec2):
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 1.0
    similarity = dot / (norm1 * norm2)
    return 1.0 - similarity


def score_to_confidence(score: float) -> float:
    """
    Lower score = higher confidence.
    Maps typical match score range to 0-100.
    """
    conf = 100.0 * (1.0 - min(max((score - 0.05) / 0.65, 0.0), 1.0))
    return round(conf, 2)


# -----------------------------------
# FACE / EMBEDDING HELPERS
# -----------------------------------
def detect_faces(image_path: str):
    try:
        return DeepFace.extract_faces(
            img_path=image_path,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=False,
            align=True
        )
    except Exception as e:
        print(f"[FACE DETECT ERROR] {image_path} -> {str(e)}")
        return []


def get_embedding_from_crop(image_path: str, model_name: str):
    try:
        reps = DeepFace.represent(
            img_path=image_path,
            model_name=model_name,
            detector_backend="skip",
            enforce_detection=False,
            align=True
        )
        if not reps:
            print(f"[WARN] No embedding for crop: {image_path} | model={model_name}")
            return None
        return l2_normalize(reps[0]["embedding"])
    except Exception as e:
        print(f"[EMBEDDING ERROR] {image_path} | model={model_name} -> {str(e)}")
        return None


def get_embeddings_for_crop(image_path: str) -> Dict[str, List[float]]:
    result = {}
    for model_name in MODELS.keys():
        emb = get_embedding_from_crop(image_path, model_name)
        if emb is not None:
            result[model_name] = emb
    return result


def save_largest_reference_crop(image_path: str, out_dir: str):
    faces = detect_faces(image_path)
    print("[REFERENCE FACES DETECTED]", len(faces))

    if len(faces) == 0:
        return None, 0

    try:
        image = Image.open(image_path).convert("RGB")
    except Exception as e:
        print("[REFERENCE IMAGE OPEN ERROR]", str(e))
        return None, 0

    best_face = None
    best_area = 0

    for idx, face in enumerate(faces):
        area = face.get("facial_area", {})
        x = int(area.get("x", 0))
        y = int(area.get("y", 0))
        w = int(area.get("w", 0))
        h = int(area.get("h", 0))
        face_area = w * h

        print(f"[REFERENCE FACE {idx}] x={x}, y={y}, w={w}, h={h}, area={face_area}")

        if face_area > best_area:
            best_area = face_area
            best_face = (x, y, w, h)

    if best_face is None:
        return None, 0

    x, y, w, h = best_face
    crop = image.crop((x, y, x + w, y + h))

    base = os.path.basename(image_path)
    crop_name = f"ref_{os.path.splitext(base)[0]}.jpg"
    crop_path = os.path.join(out_dir, crop_name)
    crop.save(crop_path)

    print("[REFERENCE CROP SAVED]", crop_name)
    return crop_path, best_area


# -----------------------------------
# CLUSTERING
# -----------------------------------
def assign_clusters(records):
    """
    Auto-cluster indexed faces per event using ArcFace score.
    This groups likely same-person faces across different photos.
    """
    clusters = []

    for idx, record in enumerate(records):
        arc_emb = record.get("embeddings", {}).get("ArcFace")
        if not arc_emb:
            record["cluster_id"] = None
            continue

        best_cluster = None
        best_score = 999

        for cluster in clusters:
            cluster_arc = cluster["arc_centroid"]
            arc_score = cosine_distance(arc_emb, cluster_arc)

            if arc_score < best_score:
                best_score = arc_score
                best_cluster = cluster

        if best_cluster is not None and best_score <= CLUSTER_ARC_THRESHOLD:
            record["cluster_id"] = best_cluster["cluster_id"]
            best_cluster["members"].append(record)
            member_embs = [
                m["embeddings"]["ArcFace"]
                for m in best_cluster["members"]
                if "ArcFace" in m.get("embeddings", {})
            ]
            best_cluster["arc_centroid"] = average_embeddings(member_embs)
        else:
            cluster_id = f"person_{len(clusters) + 1}"
            record["cluster_id"] = cluster_id
            clusters.append({
                "cluster_id": cluster_id,
                "members": [record],
                "arc_centroid": arc_emb
            })

    return records, clusters


# -----------------------------------
# ROOT
# -----------------------------------
@app.get("/")
def root():
    return {"message": "AI service running"}


# -----------------------------------
# INDEX EVENT PHOTO
# -----------------------------------
@app.post("/index-photo")
async def index_photo(event_code: str = Form(...), file: UploadFile = File(...)):
    print("\n==================================================")
    print("INDEXING EVENT PHOTO")
    print("==================================================")
    print("[EVENT CODE]", event_code)
    print("[FILE NAME ]", file.filename)

    temp_path = None

    try:
        temp_path = save_upload_to_temp(file, prefix=f"{event_code}_")
        print("[TEMP PATH ]", temp_path)

        if not os.path.exists(temp_path):
            print("[ERROR] Temp photo path does not exist")
            return {
                "filename": os.path.basename(temp_path),
                "faces_indexed": 0,
                "error": "Temp photo path does not exist"
            }

        records = load_event_embeddings(event_code)
        crop_dir = event_crop_dir(event_code)
        filename = os.path.basename(temp_path)

        records = [r for r in records if r["filename"] != filename]

        faces = detect_faces(temp_path)
        print("[FACES DETECTED]", len(faces))

        try:
            image = Image.open(temp_path).convert("RGB")
        except Exception as e:
            print("[IMAGE OPEN ERROR]", str(e))
            return {
                "filename": filename,
                "faces_indexed": 0,
                "error": f"Unable to open image: {str(e)}"
            }

        face_records = []

        for idx, face in enumerate(faces):
            try:
                area = face.get("facial_area", {})
                x = int(area.get("x", 0))
                y = int(area.get("y", 0))
                w = int(area.get("w", 0))
                h = int(area.get("h", 0))
                face_area = w * h

                print(f"\n[FACE {idx}] x={x}, y={y}, w={w}, h={h}, area={face_area}")

                if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
                    print(f"[SKIP FACE {idx}] Too small for indexing (MIN_FACE_SIZE={MIN_FACE_SIZE})")
                    continue

                crop = image.crop((x, y, x + w, y + h))
                crop_filename = f"{os.path.splitext(filename)[0]}_face_{idx}.jpg"
                crop_path = os.path.join(crop_dir, crop_filename)
                crop.save(crop_path)

                embeddings = get_embeddings_for_crop(crop_path)
                if not embeddings:
                    print(f"[SKIP FACE {idx}] No embeddings created")
                    continue

                print(f"[INDEX FACE {idx}] success | crop={crop_filename} | models={list(embeddings.keys())}")

                face_records.append({
                    "filename": filename,
                    "crop_filename": crop_filename,
                    "crop_path": crop_path,
                    "embeddings": embeddings,
                    "face_area": face_area
                })

            except Exception as e:
                print(f"[FACE {idx} PROCESS ERROR] {str(e)}")
                continue

        records.extend(face_records)

        records, clusters = assign_clusters(records)
        save_event_embeddings(event_code, records)

        print(f"[DONE] Faces indexed: {len(face_records)}")
        print(f"[CLUSTERS] Total clusters now: {len(clusters)}")

        return {
            "filename": filename,
            "faces_indexed": len(face_records),
            "clusters_total": len(clusters)
        }

    except Exception as e:
        print("[INDEX ROUTE ERROR]", str(e))
        return {
            "filename": os.path.basename(temp_path) if temp_path else (file.filename or "unknown"),
            "faces_indexed": 0,
            "error": str(e)
        }
    finally:
        if temp_path:
            cleanup_file(temp_path)


# -----------------------------------
# MATCH SELFIES
# -----------------------------------
@app.post("/match-selfie")
async def match_selfie(event_code: str = Form(...), files: List[UploadFile] = File(...)):
    print("\n==================================================")
    print("MATCHING STARTED")
    print("==================================================")
    print("[EVENT CODE  ]", event_code)
    print("[FILES COUNT ]", len(files))

    temp_selfie_paths = []

    try:
        records = load_event_embeddings(event_code)
        if not records:
            print("[WARN] No indexed faces found for this event")
            return {"matches": [], "count": 0, "ranked_matches": []}

        records, clusters = assign_clusters(records)
        save_event_embeddings(event_code, records)

        print("[INDEXED FACE RECORDS FOUND]", len(records))
        print("[CLUSTERS FOUND]", len(clusters))

        reference_embeddings_by_model: Dict[str, List[List[float]]] = {m: [] for m in MODELS.keys()}

        for i, upload_file in enumerate(files):
            print(f"\n----------------------------------")
            print(f"REFERENCE PHOTO {i + 1}")
            print(f"----------------------------------")
            print("[FILE]", upload_file.filename)

            temp_path = save_upload_to_temp(upload_file, prefix=f"ref_{event_code}_{i}_")
            temp_selfie_paths.append(temp_path)

            if not os.path.exists(temp_path):
                print("[WARN] File does not exist")
                continue

            crop_path, crop_area = save_largest_reference_crop(temp_path, REF_CROPS_DIR)
            if crop_path is None:
                print("[WARN] Could not create reference crop")
                continue

            ref_embeddings = get_embeddings_for_crop(crop_path)
            if ref_embeddings:
                for model_name, emb in ref_embeddings.items():
                    reference_embeddings_by_model[model_name].append(emb)
                print("[OK] Reference embeddings created | crop area =", crop_area)

        if len(reference_embeddings_by_model["ArcFace"]) < 2 or len(reference_embeddings_by_model["Facenet512"]) < 2:
            print("[ERROR] Need at least 2 valid references for both ArcFace and Facenet512")
            return {"matches": [], "count": 0, "ranked_matches": []}

        centroid_by_model = {
            model_name: average_embeddings(embs)
            for model_name, embs in reference_embeddings_by_model.items()
        }

        print("\n[REFERENCE CENTROIDS READY]")
        for model_name in MODELS.keys():
            print(f" - {model_name}: {len(reference_embeddings_by_model[model_name])} refs")

        scored = []

        print("\n==================================================")
        print("COMPARING INDEXED FACES")
        print("==================================================")

        for record in records:
            try:
                if "embeddings" not in record:
                    continue

                model_distances = {}
                weighted_score = 0.0
                total_weight = 0.0
                valid = True

                for model_name, model_cfg in MODELS.items():
                    face_emb = record["embeddings"].get(model_name)
                    if face_emb is None:
                        valid = False
                        break

                    centroid_dist = cosine_distance(centroid_by_model[model_name], face_emb)
                    ref_dists = [
                        cosine_distance(ref_emb, face_emb)
                        for ref_emb in reference_embeddings_by_model[model_name]
                    ]
                    min_ref_dist = min(ref_dists)

                    model_score = (0.65 * centroid_dist) + (0.35 * min_ref_dist)

                    model_distances[model_name] = {
                        "centroid": centroid_dist,
                        "min_ref": min_ref_dist,
                        "score": model_score
                    }

                    weighted_score += model_score * model_cfg["weight"]
                    total_weight += model_cfg["weight"]

                if total_weight == 0 or not valid:
                    continue

                arc_score = model_distances["ArcFace"]["score"]
                facenet_score = model_distances["Facenet512"]["score"]

                model_pass = (
                    (arc_score <= 0.62 and facenet_score <= 0.50)
                    or
                    (arc_score <= 0.52 and facenet_score <= 0.58)
                )

                final_score = weighted_score / total_weight

                face_area = record.get("face_area", 0)
                if face_area < 500:
                    final_score += 0.04
                elif face_area < 1000:
                    final_score += 0.02

                confidence = score_to_confidence(final_score)

                print(
                    "[COMPARE]",
                    "photo =", record["filename"],
                    "| crop =", record["crop_filename"],
                    "| cluster =", record.get("cluster_id"),
                    "| arc =", round(arc_score, 6),
                    "| facenet =", round(facenet_score, 6),
                    "| area =", face_area,
                    "| final =", round(final_score, 6),
                    "| confidence =", confidence,
                    "| pass =", model_pass
                )

                scored.append({
                    "filename": record["filename"],
                    "crop_filename": record["crop_filename"],
                    "cluster_id": record.get("cluster_id"),
                    "score": final_score,
                    "confidence": confidence,
                    "face_area": face_area,
                    "model_pass": model_pass,
                    "arc_score": arc_score,
                    "facenet_score": facenet_score
                })

            except Exception as e:
                print("[COMPARE ERROR]", str(e))
                continue

        if not scored:
            print("[WARN] No scored entries found")
            return {"matches": [], "count": 0, "ranked_matches": []}

        passed = [x for x in scored if x["model_pass"]]
        if not passed:
            print("[WARN] No entries passed model rules")
            return {"matches": [], "count": 0, "ranked_matches": []}

        passed.sort(key=lambda x: x["score"])
        best_score = passed[0]["score"]

        threshold = max(0.58, min(best_score + 0.16, 0.68))

        print("\n[BEST SCORE]", round(best_score, 6))
        print("[THRESHOLD ]", round(threshold, 6))

        filtered = [x for x in passed if x["score"] <= threshold]
        print("[ENTRIES WITHIN THRESHOLD]", len(filtered))

        best_per_photo = {}
        for item in filtered:
            filename = item["filename"]
            if filename not in best_per_photo or item["score"] < best_per_photo[filename]["score"]:
                best_per_photo[filename] = item

        final_items = sorted(best_per_photo.values(), key=lambda x: x["score"])
        final = [item["filename"] for item in final_items]

        print("\n==================================================")
        print("FINAL MATCHES")
        print("==================================================")
        for item in final_items:
            print(
                "photo =", item["filename"],
                "| cluster =", item["cluster_id"],
                "| final =", round(item["score"], 6),
                "| confidence =", item["confidence"],
                "| arc =", round(item["arc_score"], 6),
                "| facenet =", round(item["facenet_score"], 6),
                "| area =", item["face_area"]
            )

        print("[TOTAL FINAL MATCHES]", len(final))

        return {
            "matches": final,
            "count": len(final),
            "ranked_matches": final_items
        }

    except Exception as e:
        print("[MATCH ROUTE ERROR]", str(e))
        return {
            "matches": [],
            "count": 0,
            "ranked_matches": [],
            "error": str(e)
        }
    finally:
        for temp_path in temp_selfie_paths:
            cleanup_file(temp_path)


# -----------------------------------
# OPTIONAL: CLUSTER SUMMARY
# -----------------------------------
@app.get("/cluster-summary/{event_code}")
def cluster_summary(event_code: str):
    records = load_event_embeddings(event_code)
    if not records:
        return {"event_code": event_code, "clusters": []}

    records, clusters = assign_clusters(records)
    save_event_embeddings(event_code, records)

    summary = []
    for c in clusters:
        summary.append({
            "cluster_id": c["cluster_id"],
            "count": len(c["members"]),
            "photos": sorted(list(set([m["filename"] for m in c["members"]])))
        })

    return {
        "event_code": event_code,
        "clusters": summary
    }


