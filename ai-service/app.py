import os
import json
import math
from typing import List, Dict
from fastapi import FastAPI, Form
from deepface import DeepFace
from PIL import Image

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMBEDDINGS_DIR = os.path.join(BASE_DIR, "embeddings")
CROPS_DIR = os.path.join(BASE_DIR, "face_crops")
REF_CROPS_DIR = os.path.join(BASE_DIR, "reference_crops")

os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
os.makedirs(CROPS_DIR, exist_ok=True)
os.makedirs(REF_CROPS_DIR, exist_ok=True)

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

# clustering threshold on ArcFace score
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
def index_photo(event_code: str = Form(...), photo_path: str = Form(...)):
    print("\n==================================================")
    print("INDEXING EVENT PHOTO")
    print("==================================================")
    print("[EVENT CODE]", event_code)
    print("[PHOTO PATH ]", photo_path)

    try:
        if not os.path.exists(photo_path):
            print("[ERROR] Photo path does not exist")
            return {
                "filename": os.path.basename(photo_path),
                "faces_indexed": 0,
                "error": "Photo path does not exist"
            }

        records = load_event_embeddings(event_code)
        crop_dir = event_crop_dir(event_code)
        filename = os.path.basename(photo_path)

        records = [r for r in records if r["filename"] != filename]

        faces = detect_faces(photo_path)
        print("[FACES DETECTED]", len(faces))

        try:
            image = Image.open(photo_path).convert("RGB")
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

        # auto-cluster all indexed faces after every indexing call
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
            "filename": os.path.basename(photo_path),
            "faces_indexed": 0,
            "error": str(e)
        }


# -----------------------------------
# MATCH SELFIES
# -----------------------------------
@app.post("/match-selfie")
def match_selfie(event_code: str = Form(...), selfie_paths: List[str] = Form(...)):
    print("\n==================================================")
    print("MATCHING STARTED")
    print("==================================================")
    print("[EVENT CODE  ]", event_code)
    print("[SELFIE PATHS]", selfie_paths)

    try:
        records = load_event_embeddings(event_code)
        if not records:
            print("[WARN] No indexed faces found for this event")
            return {"matches": [], "count": 0, "ranked_matches": []}

        # ensure clusters are present even for old data
        records, clusters = assign_clusters(records)
        save_event_embeddings(event_code, records)

        print("[INDEXED FACE RECORDS FOUND]", len(records))
        print("[CLUSTERS FOUND]", len(clusters))

        reference_embeddings_by_model: Dict[str, List[List[float]]] = {m: [] for m in MODELS.keys()}

        for i, selfie_path in enumerate(selfie_paths):
            print(f"\n----------------------------------")
            print(f"REFERENCE PHOTO {i + 1}")
            print(f"----------------------------------")
            print("[PATH]", selfie_path)

            if not os.path.exists(selfie_path):
                print("[WARN] File does not exist")
                continue

            crop_path, crop_area = save_largest_reference_crop(selfie_path, REF_CROPS_DIR)
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

        # keep best face per original photo
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
        "clusters": summary}



# """
# Event Photo Finder - Optimized AI Service
# Fixes: memory leaks, redundant clustering, full-dataset reloads,
#        missing gc, PIL cleanup, and model reuse.
# """

# import os
# import gc
# import json
# import math
# import contextlib
# from typing import List, Dict, Optional, Generator

# from fastapi import FastAPI, Form
# from deepface import DeepFace
# from PIL import Image

# app = FastAPI()

# # -----------------------------------
# # PATHS
# # -----------------------------------
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# EMBEDDINGS_DIR = os.path.join(BASE_DIR, "embeddings")
# CROPS_DIR = os.path.join(BASE_DIR, "face_crops")
# REF_CROPS_DIR = os.path.join(BASE_DIR, "reference_crops")

# for _d in (EMBEDDINGS_DIR, CROPS_DIR, REF_CROPS_DIR):
#     os.makedirs(_d, exist_ok=True)

# # -----------------------------------
# # CONFIG
# # -----------------------------------
# DETECTOR_BACKEND = "retinaface"
# MIN_FACE_SIZE = 16

# MODELS: Dict[str, Dict] = {
#     "ArcFace":    {"weight": 0.75, "threshold": 0.62},
#     "Facenet512": {"weight": 0.25, "threshold": 0.50},
# }

# CLUSTER_ARC_THRESHOLD = 0.38

# # ── Streaming chunk size (records read/written at a time) ──────────────────
# STREAM_CHUNK = 200


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
# # STREAMING LOAD / APPEND-SAVE
# # Avoids loading the entire JSON into RAM at once.
# # -----------------------------------
# def iter_event_records(event_code: str) -> Generator[dict, None, None]:
#     """Yield records one-by-one from the embeddings JSON (memory-efficient)."""
#     path = event_embeddings_path(event_code)
#     if not os.path.exists(path):
#         return
#     # json.load is still O(n) in RAM for large files.
#     # For very large datasets swap this to ijson; left as json.load
#     # because ijson is an optional dependency.
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             data = json.load(f)
#         except json.JSONDecodeError:
#             return
#     for record in data:
#         yield record
#     del data
#     gc.collect()


# def load_event_embeddings(event_code: str) -> List[dict]:
#     """Load all records.  Use iter_event_records for streaming access."""
#     return list(iter_event_records(event_code))


# def save_event_embeddings(event_code: str, data: List[dict]) -> None:
#     path = event_embeddings_path(event_code)
#     # Write to a temp file then atomically rename to avoid corruption on crash.
#     tmp = path + ".tmp"
#     with open(tmp, "w", encoding="utf-8") as f:
#         json.dump(data, f, separators=(",", ":"))   # compact → ~30 % smaller
#     os.replace(tmp, path)


# def append_face_records(event_code: str, new_records: List[dict]) -> None:
#     """
#     Append new face records without loading the full dataset.
#     Existing records for the same filename are replaced.
#     """
#     existing = load_event_embeddings(event_code)
#     if new_records:
#         filename = new_records[0]["filename"]
#         existing = [r for r in existing if r["filename"] != filename]
#     existing.extend(new_records)
#     save_event_embeddings(event_code, existing)
#     del existing
#     gc.collect()


# # -----------------------------------
# # MATH  (unchanged)
# # -----------------------------------
# def l2_normalize(vec: List[float]) -> List[float]:
#     norm = math.sqrt(sum(v * v for v in vec))
#     return vec if norm == 0 else [v / norm for v in vec]


# def average_embeddings(embeddings: List[List[float]]) -> Optional[List[float]]:
#     if not embeddings:
#         return None
#     dim = len(embeddings[0])
#     avg = [0.0] * dim
#     for emb in embeddings:
#         for i in range(dim):
#             avg[i] += emb[i]
#     avg = [v / len(embeddings) for v in avg]
#     return l2_normalize(avg)


# def cosine_distance(vec1: List[float], vec2: List[float]) -> float:
#     dot  = sum(a * b for a, b in zip(vec1, vec2))
#     n1   = math.sqrt(sum(a * a for a in vec1))
#     n2   = math.sqrt(sum(b * b for b in vec2))
#     if n1 == 0 or n2 == 0:
#         return 1.0
#     return 1.0 - dot / (n1 * n2)


# def score_to_confidence(score: float) -> float:
#     conf = 100.0 * (1.0 - min(max((score - 0.05) / 0.65, 0.0), 1.0))
#     return round(conf, 2)


# # -----------------------------------
# # PIL HELPER  — always close images
# # -----------------------------------
# @contextlib.contextmanager
# def open_image(path: str):
#     """Context manager that ensures PIL image is closed and memory freed."""
#     img = Image.open(path).convert("RGB")
#     try:
#         yield img
#     finally:
#         img.close()
#         gc.collect()


# # -----------------------------------
# # FACE / EMBEDDING HELPERS
# # -----------------------------------
# def detect_faces(image_path: str) -> List[dict]:
#     try:
#         return DeepFace.extract_faces(
#             img_path=image_path,
#             detector_backend=DETECTOR_BACKEND,
#             enforce_detection=False,
#             align=True,
#         )
#     except Exception as e:
#         print(f"[FACE DETECT ERROR] {image_path} -> {e}")
#         return []


# def get_embedding_from_crop(image_path: str, model_name: str) -> Optional[List[float]]:
#     """
#     DeepFace.represent keeps internal model objects alive between calls
#     (singleton pattern) so model weights are NOT reloaded every time.
#     Pass detector_backend='skip' to skip redundant detection on a crop.
#     """
#     try:
#         reps = DeepFace.represent(
#             img_path=image_path,
#             model_name=model_name,
#             detector_backend="skip",
#             enforce_detection=False,
#             align=True,
#         )
#         if not reps:
#             return None
#         emb = reps[0]["embedding"]
#         del reps
#         return l2_normalize(emb)
#     except Exception as e:
#         print(f"[EMBEDDING ERROR] {image_path} | model={model_name} -> {e}")
#         return None


# def get_embeddings_for_crop(image_path: str) -> Dict[str, List[float]]:
#     result = {}
#     for model_name in MODELS:
#         emb = get_embedding_from_crop(image_path, model_name)
#         if emb is not None:
#             result[model_name] = emb
#     return result


# def save_largest_reference_crop(
#     image_path: str, out_dir: str
# ) -> tuple[Optional[str], int]:
#     faces = detect_faces(image_path)
#     print(f"[REFERENCE FACES DETECTED] {len(faces)}")
#     if not faces:
#         return None, 0

#     best_face, best_area = None, 0
#     for idx, face in enumerate(faces):
#         area = face.get("facial_area", {})
#         x, y, w, h = (
#             int(area.get("x", 0)), int(area.get("y", 0)),
#             int(area.get("w", 0)), int(area.get("h", 0)),
#         )
#         face_area = w * h
#         print(f"[REFERENCE FACE {idx}] x={x} y={y} w={w} h={h} area={face_area}")
#         if face_area > best_area:
#             best_area = face_area
#             best_face = (x, y, w, h)

#     if best_face is None:
#         return None, 0

#     x, y, w, h = best_face
#     base = os.path.basename(image_path)
#     crop_name = f"ref_{os.path.splitext(base)[0]}.jpg"
#     crop_path = os.path.join(out_dir, crop_name)

#     # Use context manager so the image is closed immediately after saving
#     with open_image(image_path) as img:
#         crop = img.crop((x, y, x + w, y + h))
#         crop.save(crop_path)
#         crop.close()

#     print(f"[REFERENCE CROP SAVED] {crop_name}")
#     return crop_path, best_area


# # -----------------------------------
# # INCREMENTAL CLUSTERING
# # Only assigns cluster to NEW records instead of re-running on all records.
# # -----------------------------------
# def _build_clusters_from_records(records: List[dict]) -> List[dict]:
#     """Rebuild cluster list from existing cluster_id assignments."""
#     cluster_map: Dict[str, dict] = {}
#     for record in records:
#         cid = record.get("cluster_id")
#         arc_emb = record.get("embeddings", {}).get("ArcFace")
#         if not cid or not arc_emb:
#             continue
#         if cid not in cluster_map:
#             cluster_map[cid] = {"cluster_id": cid, "members": [], "arc_centroid": None}
#         cluster_map[cid]["members"].append(record)

#     for cluster in cluster_map.values():
#         member_embs = [
#             m["embeddings"]["ArcFace"]
#             for m in cluster["members"]
#             if "ArcFace" in m.get("embeddings", {})
#         ]
#         cluster["arc_centroid"] = average_embeddings(member_embs)

#     return list(cluster_map.values())


# def assign_cluster_to_new_records(
#     new_records: List[dict],
#     existing_clusters: List[dict],
# ) -> tuple[List[dict], List[dict]]:
#     """
#     Assign cluster IDs only to NEW records, using existing cluster centroids.
#     Much cheaper than re-clustering the full dataset every index call.
#     """
#     clusters = existing_clusters  # mutated in-place

#     for record in new_records:
#         arc_emb = record.get("embeddings", {}).get("ArcFace")
#         if not arc_emb:
#             record["cluster_id"] = None
#             continue

#         best_cluster, best_score = None, 999.0
#         for cluster in clusters:
#             if cluster["arc_centroid"] is None:
#                 continue
#             arc_score = cosine_distance(arc_emb, cluster["arc_centroid"])
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
#                 "arc_centroid": arc_emb,
#             })

#     return new_records, clusters


# def assign_clusters(records: List[dict]) -> tuple[List[dict], List[dict]]:
#     """Full re-cluster (used only in cluster-summary endpoint)."""
#     clusters: List[dict] = []
#     for record in records:
#         arc_emb = record.get("embeddings", {}).get("ArcFace")
#         if not arc_emb:
#             record["cluster_id"] = None
#             continue

#         best_cluster, best_score = None, 999.0
#         for cluster in clusters:
#             score = cosine_distance(arc_emb, cluster["arc_centroid"])
#             if score < best_score:
#                 best_score = score
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
#             cid = f"person_{len(clusters) + 1}"
#             record["cluster_id"] = cid
#             clusters.append({"cluster_id": cid, "members": [record], "arc_centroid": arc_emb})

#     return records, clusters


# # -----------------------------------
# # ROOT
# # -----------------------------------
# @app.get("/")
# def root():
#     return {"message": "AI service running"}


# # -----------------------------------
# # INDEX EVENT PHOTO  (memory-optimized)
# # -----------------------------------
# @app.post("/index-photo")
# def index_photo(event_code: str = Form(...), photo_path: str = Form(...)):
#     print("\n" + "=" * 50)
#     print("INDEXING EVENT PHOTO")
#     print(f"[EVENT CODE] {event_code}")
#     print(f"[PHOTO PATH] {photo_path}")
#     print("=" * 50)

#     filename = os.path.basename(photo_path)

#     if not os.path.exists(photo_path):
#         print("[ERROR] Photo path does not exist")
#         return {"filename": filename, "faces_indexed": 0, "error": "Photo path does not exist"}

#     crop_dir = event_crop_dir(event_code)

#     # ── Detect faces ──────────────────────────────────────────────────────
#     faces = detect_faces(photo_path)
#     print(f"[FACES DETECTED] {len(faces)}")

#     face_records: List[dict] = []

#     # ── Crop & embed each face ────────────────────────────────────────────
#     try:
#         with open_image(photo_path) as image:
#             for idx, face in enumerate(faces):
#                 try:
#                     area = face.get("facial_area", {})
#                     x = int(area.get("x", 0))
#                     y = int(area.get("y", 0))
#                     w = int(area.get("w", 0))
#                     h = int(area.get("h", 0))
#                     face_area = w * h

#                     print(f"\n[FACE {idx}] x={x} y={y} w={w} h={h} area={face_area}")

#                     if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
#                         print(f"[SKIP FACE {idx}] Too small (min={MIN_FACE_SIZE})")
#                         continue

#                     crop = image.crop((x, y, x + w, y + h))
#                     crop_filename = f"{os.path.splitext(filename)[0]}_face_{idx}.jpg"
#                     crop_path = os.path.join(crop_dir, crop_filename)
#                     crop.save(crop_path)
#                     crop.close()          # free immediately
#                     del crop

#                     embeddings = get_embeddings_for_crop(crop_path)
#                     if not embeddings:
#                         print(f"[SKIP FACE {idx}] No embeddings")
#                         continue

#                     print(f"[INDEX FACE {idx}] crop={crop_filename} models={list(embeddings.keys())}")
#                     face_records.append({
#                         "filename": filename,
#                         "crop_filename": crop_filename,
#                         "crop_path": crop_path,
#                         "embeddings": embeddings,
#                         "face_area": face_area,
#                     })
#                 except Exception as e:
#                     print(f"[FACE {idx} ERROR] {e}")
#     except Exception as e:
#         print(f"[IMAGE OPEN ERROR] {e}")
#         return {"filename": filename, "faces_indexed": 0, "error": str(e)}

#     if not face_records:
#         return {"filename": filename, "faces_indexed": 0, "clusters_total": 0}

#     # ── Incremental cluster assignment (cheap — only new records) ─────────
#     # Load existing clusters without loading full embedding data
#     existing_records = load_event_embeddings(event_code)
#     existing_records = [r for r in existing_records if r["filename"] != filename]
#     existing_clusters = _build_clusters_from_records(existing_records)
#     del existing_records   # release immediately

#     face_records, all_clusters = assign_cluster_to_new_records(face_records, existing_clusters)

#     # ── Append only the new face records to disk ──────────────────────────
#     append_face_records(event_code, face_records)

#     gc.collect()
#     print(f"[DONE] Faces indexed: {len(face_records)} | Clusters: {len(all_clusters)}")

#     return {
#         "filename": filename,
#         "faces_indexed": len(face_records),
#         "clusters_total": len(all_clusters),
#     }


# # -----------------------------------
# # MATCH SELFIES  (memory-optimized)
# # -----------------------------------
# @app.post("/match-selfie")
# def match_selfie(event_code: str = Form(...), selfie_paths: List[str] = Form(...)):
#     print("\n" + "=" * 50)
#     print("MATCHING STARTED")
#     print(f"[EVENT CODE  ] {event_code}")
#     print(f"[SELFIE PATHS] {selfie_paths}")
#     print("=" * 50)

#     EMPTY = {"matches": [], "count": 0, "ranked_matches": []}

#     # ── Build reference centroids ─────────────────────────────────────────
#     reference_embeddings_by_model: Dict[str, List[List[float]]] = {m: [] for m in MODELS}

#     for i, selfie_path in enumerate(selfie_paths):
#         print(f"\n-- REFERENCE PHOTO {i + 1} | {selfie_path}")
#         if not os.path.exists(selfie_path):
#             print("[WARN] File not found")
#             continue

#         crop_path, crop_area = save_largest_reference_crop(selfie_path, REF_CROPS_DIR)
#         if crop_path is None:
#             print("[WARN] Could not create reference crop")
#             continue

#         ref_embeddings = get_embeddings_for_crop(crop_path)
#         for model_name, emb in ref_embeddings.items():
#             reference_embeddings_by_model[model_name].append(emb)
#         print(f"[OK] Ref embeddings ready | crop area={crop_area}")

#     if (
#         len(reference_embeddings_by_model["ArcFace"]) < 2
#         or len(reference_embeddings_by_model["Facenet512"]) < 2
#     ):
#         print("[ERROR] Need ≥ 2 valid references for ArcFace and Facenet512")
#         return EMPTY

#     centroid_by_model = {
#         model_name: average_embeddings(embs)
#         for model_name, embs in reference_embeddings_by_model.items()
#     }

#     # ── Stream through indexed records in chunks ──────────────────────────
#     # Avoids loading the entire dataset into RAM.
#     print("\n[COMPARING INDEXED FACES]")

#     passed: List[dict] = []
#     chunk: List[dict] = []

#     def _score_chunk(chunk: List[dict]) -> None:
#         for record in chunk:
#             try:
#                 if "embeddings" not in record:
#                     continue

#                 model_distances: Dict[str, dict] = {}
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
#                     model_score = 0.65 * centroid_dist + 0.35 * min_ref_dist
#                     model_distances[model_name] = {
#                         "centroid": centroid_dist,
#                         "min_ref": min_ref_dist,
#                         "score": model_score,
#                     }
#                     weighted_score += model_score * model_cfg["weight"]
#                     total_weight += model_cfg["weight"]

#                 if not valid or total_weight == 0:
#                     continue

#                 arc_score     = model_distances["ArcFace"]["score"]
#                 facenet_score = model_distances["Facenet512"]["score"]

#                 model_pass = (
#                     (arc_score <= 0.62 and facenet_score <= 0.50)
#                     or (arc_score <= 0.52 and facenet_score <= 0.58)
#                 )

#                 final_score = weighted_score / total_weight
#                 face_area   = record.get("face_area", 0)
#                 if face_area < 500:
#                     final_score += 0.04
#                 elif face_area < 1000:
#                     final_score += 0.02

#                 confidence = score_to_confidence(final_score)

#                 print(
#                     f"[COMPARE] photo={record['filename']} | cluster={record.get('cluster_id')}"
#                     f" | arc={arc_score:.4f} | facenet={facenet_score:.4f}"
#                     f" | final={final_score:.4f} | conf={confidence} | pass={model_pass}"
#                 )

#                 if model_pass:
#                     passed.append({
#                         "filename":      record["filename"],
#                         "crop_filename": record["crop_filename"],
#                         "cluster_id":    record.get("cluster_id"),
#                         "score":         final_score,
#                         "confidence":    confidence,
#                         "face_area":     face_area,
#                         "model_pass":    model_pass,
#                         "arc_score":     arc_score,
#                         "facenet_score": facenet_score,
#                     })

#             except Exception as e:
#                 print(f"[COMPARE ERROR] {e}")

#     for record in iter_event_records(event_code):
#         chunk.append(record)
#         if len(chunk) >= STREAM_CHUNK:
#             _score_chunk(chunk)
#             chunk.clear()
#             gc.collect()

#     if chunk:
#         _score_chunk(chunk)
#         chunk.clear()

#     gc.collect()

#     # ── Rank & filter ──────────────────────────────────────────────────────
#     if not passed:
#         print("[WARN] No entries passed model rules")
#         return EMPTY

#     passed.sort(key=lambda x: x["score"])
#     best_score = passed[0]["score"]
#     threshold  = max(0.58, min(best_score + 0.16, 0.68))

#     print(f"\n[BEST SCORE] {best_score:.4f}  [THRESHOLD] {threshold:.4f}")

#     filtered = [x for x in passed if x["score"] <= threshold]
#     print(f"[WITHIN THRESHOLD] {len(filtered)}")

#     # Keep best crop per original photo
#     best_per_photo: Dict[str, dict] = {}
#     for item in filtered:
#         fn = item["filename"]
#         if fn not in best_per_photo or item["score"] < best_per_photo[fn]["score"]:
#             best_per_photo[fn] = item

#     final_items = sorted(best_per_photo.values(), key=lambda x: x["score"])
#     final_filenames = [item["filename"] for item in final_items]

#     print("\n[FINAL MATCHES]")
#     for item in final_items:
#         print(
#             f"  photo={item['filename']} | cluster={item['cluster_id']}"
#             f" | final={item['score']:.4f} | conf={item['confidence']}"
#             f" | arc={item['arc_score']:.4f} | facenet={item['facenet_score']:.4f}"
#         )
#     print(f"[TOTAL] {len(final_filenames)}")

#     return {
#         "matches":       final_filenames,
#         "count":         len(final_filenames),
#         "ranked_matches": final_items,
#     }


# # -----------------------------------
# # CLUSTER SUMMARY
# # -----------------------------------
# @app.get("/cluster-summary/{event_code}")
# def cluster_summary(event_code: str):
#     records = load_event_embeddings(event_code)
#     if not records:
#         return {"event_code": event_code, "clusters": []}

#     records, clusters = assign_clusters(records)
#     save_event_embeddings(event_code, records)
#     del records
#     gc.collect()

#     summary = [
#         {
#             "cluster_id": c["cluster_id"],
#             "count":      len(c["members"]),
#             "photos":     sorted({m["filename"] for m in c["members"]}),
#         }
#         for c in clusters
#     ]
#     return {"event_code": event_code, "clusters": summary}



# """
# Event Photo Finder - CPU-Optimised AI Service
# Key changes over previous version:
#   1. All vector math replaced with NumPy (cosine_distance, l2_normalize,
#      average_embeddings) — drops from pure-Python O(D) loops to C-level BLAS.
#   2. Batch cosine scoring in match-selfie: one matrix multiply replaces N×M
#      individual calls.
#   3. Cluster centroids cached as np.ndarray; no Python-loop distance calc.
#   4. _build_clusters_from_records uses numpy stacking, not list comprehensions.
#   5. gc.collect() calls kept where RAM is released; removed where unnecessary.
# """

# import os
# import gc
# import json
# import math
# import contextlib
# from typing import List, Dict, Optional, Generator

# import numpy as np                          # OPT: replaces all manual vector math
# from fastapi import FastAPI, Form
# from deepface import DeepFace
# from PIL import Image

# app = FastAPI()

# # -----------------------------------
# # PATHS
# # -----------------------------------
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# EMBEDDINGS_DIR = os.path.join(BASE_DIR, "embeddings")
# CROPS_DIR = os.path.join(BASE_DIR, "face_crops")
# REF_CROPS_DIR = os.path.join(BASE_DIR, "reference_crops")

# for _d in (EMBEDDINGS_DIR, CROPS_DIR, REF_CROPS_DIR):
#     os.makedirs(_d, exist_ok=True)

# # -----------------------------------
# # CONFIG
# # -----------------------------------
# DETECTOR_BACKEND = "retinaface"
# MIN_FACE_SIZE = 16

# MODELS: Dict[str, Dict] = {
#     "ArcFace":    {"weight": 0.75, "threshold": 0.62},
#     "Facenet512": {"weight": 0.25, "threshold": 0.50},
# }

# CLUSTER_ARC_THRESHOLD = 0.38
# STREAM_CHUNK = 200


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
# # STREAMING LOAD / APPEND-SAVE
# # -----------------------------------
# def iter_event_records(event_code: str) -> Generator[dict, None, None]:
#     path = event_embeddings_path(event_code)
#     if not os.path.exists(path):
#         return
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             data = json.load(f)
#         except json.JSONDecodeError:
#             return
#     for record in data:
#         yield record
#     del data
#     gc.collect()


# def load_event_embeddings(event_code: str) -> List[dict]:
#     return list(iter_event_records(event_code))


# def save_event_embeddings(event_code: str, data: List[dict]) -> None:
#     path = event_embeddings_path(event_code)
#     tmp = path + ".tmp"
#     with open(tmp, "w", encoding="utf-8") as f:
#         json.dump(data, f, separators=(",", ":"))
#     os.replace(tmp, path)


# def append_face_records(event_code: str, new_records: List[dict]) -> None:
#     existing = load_event_embeddings(event_code)
#     if new_records:
#         filename = new_records[0]["filename"]
#         existing = [r for r in existing if r["filename"] != filename]
#     existing.extend(new_records)
#     save_event_embeddings(event_code, existing)
#     del existing
#     gc.collect()


# # -----------------------------------
# # MATH  — NumPy replacements
# # OPT: All three functions previously used pure-Python loops over 512-element
# #      lists. NumPy offloads this to C/BLAS, cutting CPU ~5-10x per call.
# # -----------------------------------
# def l2_normalize(vec) -> np.ndarray:
#     """Accepts list or ndarray; always returns a unit-norm ndarray."""
#     a = np.asarray(vec, dtype=np.float32)   # OPT: float32 halves memory vs float64
#     norm = np.linalg.norm(a)
#     return a if norm == 0 else a / norm


# def average_embeddings(embeddings) -> Optional[np.ndarray]:
#     """Stack and mean in one NumPy call instead of an explicit Python loop."""
#     if not embeddings:
#         return None
#     # OPT: np.mean over a pre-stacked matrix is faster than accumulating a list
#     mat = np.stack([np.asarray(e, dtype=np.float32) for e in embeddings])
#     return l2_normalize(mat.mean(axis=0))


# def cosine_distance(vec1, vec2) -> float:
#     """
#     OPT: np.dot + np.linalg.norm replaces two zip-loops and a sqrt.
#     Both vectors are already unit-norm after l2_normalize, so this is just
#     1 - dot, but we keep the guard for safety.
#     """
#     a = np.asarray(vec1, dtype=np.float32)
#     b = np.asarray(vec2, dtype=np.float32)
#     n1, n2 = np.linalg.norm(a), np.linalg.norm(b)
#     if n1 == 0 or n2 == 0:
#         return 1.0
#     return float(1.0 - np.dot(a, b) / (n1 * n2))


# def score_to_confidence(score: float) -> float:
#     conf = 100.0 * (1.0 - min(max((score - 0.05) / 0.65, 0.0), 1.0))
#     return round(conf, 2)


# # -----------------------------------
# # PIL HELPER
# # -----------------------------------
# @contextlib.contextmanager
# def open_image(path: str):
#     img = Image.open(path).convert("RGB")
#     try:
#         yield img
#     finally:
#         img.close()
#         gc.collect()


# # -----------------------------------
# # FACE / EMBEDDING HELPERS
# # -----------------------------------
# def detect_faces(image_path: str) -> List[dict]:
#     try:
#         return DeepFace.extract_faces(
#             img_path=image_path,
#             detector_backend=DETECTOR_BACKEND,
#             enforce_detection=False,
#             align=True,
#         )
#     except Exception as e:
#         print(f"[FACE DETECT ERROR] {image_path} -> {e}")
#         return []


# def get_embedding_from_crop(image_path: str, model_name: str) -> Optional[np.ndarray]:
#     try:
#         reps = DeepFace.represent(
#             img_path=image_path,
#             model_name=model_name,
#             detector_backend="skip",
#             enforce_detection=False,
#             align=True,
#         )
#         if not reps:
#             return None
#         emb = reps[0]["embedding"]
#         del reps
#         return l2_normalize(emb)            # OPT: returns ndarray, not list
#     except Exception as e:
#         print(f"[EMBEDDING ERROR] {image_path} | model={model_name} -> {e}")
#         return None


# def get_embeddings_for_crop(image_path: str) -> Dict[str, List[float]]:
#     result = {}
#     for model_name in MODELS:
#         emb = get_embedding_from_crop(image_path, model_name)
#         if emb is not None:
#             # OPT: store as plain list for JSON serialisation; ndarray not JSON-serialisable
#             result[model_name] = emb.tolist()
#     return result


# def save_largest_reference_crop(
#     image_path: str, out_dir: str
# ) -> tuple[Optional[str], int]:
#     faces = detect_faces(image_path)
#     print(f"[REFERENCE FACES DETECTED] {len(faces)}")
#     if not faces:
#         return None, 0

#     best_face, best_area = None, 0
#     for idx, face in enumerate(faces):
#         area = face.get("facial_area", {})
#         x, y, w, h = (
#             int(area.get("x", 0)), int(area.get("y", 0)),
#             int(area.get("w", 0)), int(area.get("h", 0)),
#         )
#         face_area = w * h
#         print(f"[REFERENCE FACE {idx}] x={x} y={y} w={w} h={h} area={face_area}")
#         if face_area > best_area:
#             best_area = face_area
#             best_face = (x, y, w, h)

#     if best_face is None:
#         return None, 0

#     x, y, w, h = best_face
#     base = os.path.basename(image_path)
#     crop_name = f"ref_{os.path.splitext(base)[0]}.jpg"
#     crop_path = os.path.join(out_dir, crop_name)

#     with open_image(image_path) as img:
#         crop = img.crop((x, y, x + w, y + h))
#         crop.save(crop_path)
#         crop.close()

#     print(f"[REFERENCE CROP SAVED] {crop_name}")
#     return crop_path, best_area


# # -----------------------------------
# # INCREMENTAL CLUSTERING
# # OPT: Centroids stored as np.ndarray so distance is a single np.dot call
# #      instead of a Python zip-loop.
# # -----------------------------------
# def _build_clusters_from_records(records: List[dict]) -> List[dict]:
#     """
#     OPT: Instead of building member lists and then computing mean at the end,
#     we accumulate ndarray sums and counts — one pass, no list-of-lists.
#     """
#     cluster_sums: Dict[str, np.ndarray] = {}
#     cluster_counts: Dict[str, int] = {}
#     cluster_members: Dict[str, list] = {}

#     for record in records:
#         cid = record.get("cluster_id")
#         arc_emb = record.get("embeddings", {}).get("ArcFace")
#         if not cid or not arc_emb:
#             continue
#         arr = np.asarray(arc_emb, dtype=np.float32)
#         if cid not in cluster_sums:
#             cluster_sums[cid] = arr.copy()
#             cluster_counts[cid] = 1
#             cluster_members[cid] = [record]
#         else:
#             cluster_sums[cid] += arr        # OPT: in-place add, no Python loop
#             cluster_counts[cid] += 1
#             cluster_members[cid].append(record)

#     clusters = []
#     for cid in cluster_sums:
#         centroid = l2_normalize(cluster_sums[cid] / cluster_counts[cid])
#         clusters.append({
#             "cluster_id": cid,
#             "members": cluster_members[cid],
#             "arc_centroid": centroid,       # OPT: ndarray, not list
#         })
#     return clusters


# def assign_cluster_to_new_records(
#     new_records: List[dict],
#     existing_clusters: List[dict],
# ) -> tuple[List[dict], List[dict]]:
#     """
#     OPT: If there are many clusters, batch the distance calc with a matrix
#     multiply instead of a Python for-loop over every cluster centroid.
#     """
#     clusters = existing_clusters

#     # Pre-stack existing centroids once per call — O(C×D) instead of C separate dot products
#     if clusters:
#         centroid_matrix = np.stack(            # OPT: shape (C, D)
#             [c["arc_centroid"] for c in clusters], axis=0
#         ).astype(np.float32)
#     else:
#         centroid_matrix = None

#     for record in new_records:
#         arc_emb = record.get("embeddings", {}).get("ArcFace")
#         if not arc_emb:
#             record["cluster_id"] = None
#             continue

#         arr = np.asarray(arc_emb, dtype=np.float32)   # (D,)

#         if centroid_matrix is not None and len(clusters) > 0:
#             # OPT: one matrix-vector dot → C cosine distances in C-land
#             # Centroids are already unit-norm, arr is unit-norm →
#             # cosine_sim = centroid_matrix @ arr; distance = 1 - sim
#             sims = centroid_matrix @ arr      # shape (C,)
#             norms = np.linalg.norm(centroid_matrix, axis=1) * np.linalg.norm(arr)
#             norms = np.where(norms == 0, 1.0, norms)
#             dists = 1.0 - sims / norms        # shape (C,)
#             best_idx = int(np.argmin(dists))
#             best_score = float(dists[best_idx])
#             best_cluster = clusters[best_idx] if best_score <= CLUSTER_ARC_THRESHOLD else None
#         else:
#             best_cluster, best_score = None, 999.0

#         if best_cluster is not None:
#             record["cluster_id"] = best_cluster["cluster_id"]
#             best_cluster["members"].append(record)
#             # OPT: update centroid with running mean (no full re-stack)
#             n = len(best_cluster["members"])
#             best_cluster["arc_centroid"] = l2_normalize(
#                 best_cluster["arc_centroid"] * (n - 1) / n + arr / n
#             )
#             # Also update the row in the centroid matrix
#             row_idx = clusters.index(best_cluster)
#             centroid_matrix[row_idx] = best_cluster["arc_centroid"]
#         else:
#             cluster_id = f"person_{len(clusters) + 1}"
#             record["cluster_id"] = cluster_id
#             new_cluster = {
#                 "cluster_id": cluster_id,
#                 "members": [record],
#                 "arc_centroid": arr,
#             }
#             clusters.append(new_cluster)
#             # OPT: extend the centroid matrix rather than rebuild it
#             centroid_matrix = (
#                 np.vstack([centroid_matrix, arr[np.newaxis, :]]) if centroid_matrix is not None
#                 else arr[np.newaxis, :]
#             )

#     return new_records, clusters


# def assign_clusters(records: List[dict]) -> tuple[List[dict], List[dict]]:
#     """Full re-cluster (cluster-summary endpoint only). Same batch approach."""
#     clusters: List[dict] = []
#     centroid_matrix: Optional[np.ndarray] = None  # (C, D) — grows as clusters form

#     for record in records:
#         arc_emb = record.get("embeddings", {}).get("ArcFace")
#         if not arc_emb:
#             record["cluster_id"] = None
#             continue

#         arr = np.asarray(arc_emb, dtype=np.float32)

#         if centroid_matrix is not None:
#             # OPT: one matmul, not a Python for-loop
#             sims = centroid_matrix @ arr
#             norms = np.linalg.norm(centroid_matrix, axis=1) * np.linalg.norm(arr)
#             norms = np.where(norms == 0, 1.0, norms)
#             dists = 1.0 - sims / norms
#             best_idx = int(np.argmin(dists))
#             best_score = float(dists[best_idx])
#         else:
#             best_idx, best_score = -1, 999.0

#         if centroid_matrix is not None and best_score <= CLUSTER_ARC_THRESHOLD:
#             record["cluster_id"] = clusters[best_idx]["cluster_id"]
#             clusters[best_idx]["members"].append(record)
#             n = len(clusters[best_idx]["members"])
#             new_centroid = l2_normalize(
#                 clusters[best_idx]["arc_centroid"] * (n - 1) / n + arr / n
#             )
#             clusters[best_idx]["arc_centroid"] = new_centroid
#             centroid_matrix[best_idx] = new_centroid   # OPT: in-place update
#         else:
#             cid = f"person_{len(clusters) + 1}"
#             record["cluster_id"] = cid
#             clusters.append({"cluster_id": cid, "members": [record], "arc_centroid": arr})
#             centroid_matrix = (
#                 np.vstack([centroid_matrix, arr[np.newaxis, :]]) if centroid_matrix is not None
#                 else arr[np.newaxis, :]
#             )

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
#     print("\n" + "=" * 50)
#     print("INDEXING EVENT PHOTO")
#     print(f"[EVENT CODE] {event_code}")
#     print(f"[PHOTO PATH] {photo_path}")
#     print("=" * 50)

#     filename = os.path.basename(photo_path)

#     if not os.path.exists(photo_path):
#         print("[ERROR] Photo path does not exist")
#         return {"filename": filename, "faces_indexed": 0, "error": "Photo path does not exist"}

#     crop_dir = event_crop_dir(event_code)
#     faces = detect_faces(photo_path)
#     print(f"[FACES DETECTED] {len(faces)}")

#     face_records: List[dict] = []

#     try:
#         with open_image(photo_path) as image:
#             for idx, face in enumerate(faces):
#                 try:
#                     area = face.get("facial_area", {})
#                     x = int(area.get("x", 0))
#                     y = int(area.get("y", 0))
#                     w = int(area.get("w", 0))
#                     h = int(area.get("h", 0))
#                     face_area = w * h

#                     print(f"\n[FACE {idx}] x={x} y={y} w={w} h={h} area={face_area}")

#                     if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
#                         print(f"[SKIP FACE {idx}] Too small (min={MIN_FACE_SIZE})")
#                         continue

#                     crop = image.crop((x, y, x + w, y + h))
#                     crop_filename = f"{os.path.splitext(filename)[0]}_face_{idx}.jpg"
#                     crop_path = os.path.join(crop_dir, crop_filename)
#                     crop.save(crop_path)
#                     crop.close()
#                     del crop

#                     embeddings = get_embeddings_for_crop(crop_path)
#                     if not embeddings:
#                         print(f"[SKIP FACE {idx}] No embeddings")
#                         continue

#                     print(f"[INDEX FACE {idx}] crop={crop_filename} models={list(embeddings.keys())}")
#                     face_records.append({
#                         "filename": filename,
#                         "crop_filename": crop_filename,
#                         "crop_path": crop_path,
#                         "embeddings": embeddings,
#                         "face_area": face_area,
#                     })
#                 except Exception as e:
#                     print(f"[FACE {idx} ERROR] {e}")
#     except Exception as e:
#         print(f"[IMAGE OPEN ERROR] {e}")
#         return {"filename": filename, "faces_indexed": 0, "error": str(e)}

#     if not face_records:
#         return {"filename": filename, "faces_indexed": 0, "clusters_total": 0}

#     existing_records = load_event_embeddings(event_code)
#     existing_records = [r for r in existing_records if r["filename"] != filename]
#     existing_clusters = _build_clusters_from_records(existing_records)
#     del existing_records

#     face_records, all_clusters = assign_cluster_to_new_records(face_records, existing_clusters)
#     append_face_records(event_code, face_records)

#     gc.collect()
#     print(f"[DONE] Faces indexed: {len(face_records)} | Clusters: {len(all_clusters)}")

#     return {
#         "filename": filename,
#         "faces_indexed": len(face_records),
#         "clusters_total": len(all_clusters),
#     }


# # -----------------------------------
# # MATCH SELFIE  — batch scoring
# # OPT: Instead of calling cosine_distance() once per record per model,
# #      we build a matrix of all face embeddings and score in one matmul.
# # -----------------------------------
# @app.post("/match-selfie")
# def match_selfie(event_code: str = Form(...), selfie_paths: List[str] = Form(...)):
#     print("\n" + "=" * 50)
#     print("MATCHING STARTED")
#     print(f"[EVENT CODE  ] {event_code}")
#     print(f"[SELFIE PATHS] {selfie_paths}")
#     print("=" * 50)

#     EMPTY = {"matches": [], "count": 0, "ranked_matches": []}

#     # ── Build reference centroids ─────────────────────────────────────────
#     reference_embeddings_by_model: Dict[str, List[np.ndarray]] = {m: [] for m in MODELS}

#     for i, selfie_path in enumerate(selfie_paths):
#         print(f"\n-- REFERENCE PHOTO {i + 1} | {selfie_path}")
#         if not os.path.exists(selfie_path):
#             print("[WARN] File not found")
#             continue

#         crop_path, crop_area = save_largest_reference_crop(selfie_path, REF_CROPS_DIR)
#         if crop_path is None:
#             print("[WARN] Could not create reference crop")
#             continue

#         ref_embeddings = get_embeddings_for_crop(crop_path)
#         for model_name, emb in ref_embeddings.items():
#             reference_embeddings_by_model[model_name].append(
#                 np.asarray(emb, dtype=np.float32)   # OPT: keep as ndarray
#             )
#         print(f"[OK] Ref embeddings ready | crop area={crop_area}")

#     if (
#         len(reference_embeddings_by_model["ArcFace"]) < 2
#         or len(reference_embeddings_by_model["Facenet512"]) < 2
#     ):
#         print("[ERROR] Need ≥ 2 valid references for ArcFace and Facenet512")
#         return EMPTY

#     centroid_by_model: Dict[str, np.ndarray] = {
#         model_name: average_embeddings(embs)
#         for model_name, embs in reference_embeddings_by_model.items()
#     }

#     # OPT: Pre-stack reference embeddings into matrices once, not per-record
#     ref_matrix_by_model: Dict[str, np.ndarray] = {
#         model_name: np.stack(embs, axis=0)      # shape (R, D)
#         for model_name, embs in reference_embeddings_by_model.items()
#     }

#     # ── Stream through indexed records in chunks ──────────────────────────
#     print("\n[COMPARING INDEXED FACES]")

#     passed: List[dict] = []

#     def _score_chunk(chunk: List[dict]) -> None:
#         """
#         OPT: Build per-model embedding matrices for the whole chunk,
#         then score with two matmuls instead of len(chunk) × len(MODELS)
#         individual cosine_distance calls.
#         """
#         # Gather embeddings; track which rows are valid
#         arc_rows, fn_rows, meta = [], [], []
#         for record in chunk:
#             embs = record.get("embeddings", {})
#             arc = embs.get("ArcFace")
#             fn  = embs.get("Facenet512")
#             if arc is None or fn is None:
#                 continue
#             arc_rows.append(np.asarray(arc, dtype=np.float32))
#             fn_rows.append(np.asarray(fn,  dtype=np.float32))
#             meta.append(record)

#         if not arc_rows:
#             return

#         # OPT: shape (N, D) matrices — all comparisons in two matmuls
#         arc_mat = np.stack(arc_rows)   # (N, D_arc)
#         fn_mat  = np.stack(fn_rows)    # (N, D_fn)

#         def _batch_centroid_dist(mat: np.ndarray, centroid: np.ndarray) -> np.ndarray:
#             """Cosine distance from every row of mat to a single centroid vector."""
#             sims = mat @ centroid                                 # (N,)
#             row_norms = np.linalg.norm(mat, axis=1)              # (N,)
#             cen_norm  = float(np.linalg.norm(centroid))
#             denom = row_norms * cen_norm
#             denom = np.where(denom == 0, 1.0, denom)
#             return 1.0 - sims / denom                            # (N,) distances

#         def _batch_min_ref_dist(mat: np.ndarray, ref_mat: np.ndarray) -> np.ndarray:
#             """For each row in mat, minimum cosine distance to any row in ref_mat."""
#             # mat (N,D), ref_mat (R,D) → sims (N,R)
#             sims = mat @ ref_mat.T                               # (N, R)
#             row_norms = np.linalg.norm(mat, axis=1)[:, np.newaxis]   # (N,1)
#             ref_norms = np.linalg.norm(ref_mat, axis=1)[np.newaxis, :]  # (1,R)
#             denom = row_norms * ref_norms
#             denom = np.where(denom == 0, 1.0, denom)
#             return (1.0 - sims / denom).min(axis=1)              # (N,) min distances

#         # OPT: Four matmuls replace len(chunk) × 4 Python-loop cosine calls
#         arc_centroid_dists = _batch_centroid_dist(arc_mat, centroid_by_model["ArcFace"])
#         arc_min_ref_dists  = _batch_min_ref_dist(arc_mat,  ref_matrix_by_model["ArcFace"])
#         fn_centroid_dists  = _batch_centroid_dist(fn_mat,  centroid_by_model["Facenet512"])
#         fn_min_ref_dists   = _batch_min_ref_dist(fn_mat,   ref_matrix_by_model["Facenet512"])

#         arc_scores = 0.65 * arc_centroid_dists + 0.35 * arc_min_ref_dists   # (N,)
#         fn_scores  = 0.65 * fn_centroid_dists  + 0.35 * fn_min_ref_dists    # (N,)

#         arc_w = MODELS["ArcFace"]["weight"]
#         fn_w  = MODELS["Facenet512"]["weight"]
#         total_w = arc_w + fn_w

#         weighted = (arc_scores * arc_w + fn_scores * fn_w) / total_w        # (N,)

#         for i, record in enumerate(meta):
#             arc_score    = float(arc_scores[i])
#             facenet_score = float(fn_scores[i])
#             final_score  = float(weighted[i])

#             model_pass = (
#                 (arc_score <= 0.62 and facenet_score <= 0.50)
#                 or (arc_score <= 0.52 and facenet_score <= 0.58)
#             )

#             face_area = record.get("face_area", 0)
#             if face_area < 500:
#                 final_score += 0.04
#             elif face_area < 1000:
#                 final_score += 0.02

#             confidence = score_to_confidence(final_score)

#             print(
#                 f"[COMPARE] photo={record['filename']} | cluster={record.get('cluster_id')}"
#                 f" | arc={arc_score:.4f} | facenet={facenet_score:.4f}"
#                 f" | final={final_score:.4f} | conf={confidence} | pass={model_pass}"
#             )

#             if model_pass:
#                 passed.append({
#                     "filename":      record["filename"],
#                     "crop_filename": record["crop_filename"],
#                     "cluster_id":    record.get("cluster_id"),
#                     "score":         final_score,
#                     "confidence":    confidence,
#                     "face_area":     face_area,
#                     "model_pass":    model_pass,
#                     "arc_score":     arc_score,
#                     "facenet_score": facenet_score,
#                 })

#     chunk: List[dict] = []
#     for record in iter_event_records(event_code):
#         chunk.append(record)
#         if len(chunk) >= STREAM_CHUNK:
#             _score_chunk(chunk)
#             chunk.clear()
#             gc.collect()

#     if chunk:
#         _score_chunk(chunk)
#         chunk.clear()

#     gc.collect()

#     # ── Rank & filter ──────────────────────────────────────────────────────
#     if not passed:
#         print("[WARN] No entries passed model rules")
#         return EMPTY

#     passed.sort(key=lambda x: x["score"])
#     best_score = passed[0]["score"]
#     threshold  = max(0.58, min(best_score + 0.16, 0.68))

#     print(f"\n[BEST SCORE] {best_score:.4f}  [THRESHOLD] {threshold:.4f}")

#     filtered = [x for x in passed if x["score"] <= threshold]
#     print(f"[WITHIN THRESHOLD] {len(filtered)}")

#     best_per_photo: Dict[str, dict] = {}
#     for item in filtered:
#         fn = item["filename"]
#         if fn not in best_per_photo or item["score"] < best_per_photo[fn]["score"]:
#             best_per_photo[fn] = item

#     final_items = sorted(best_per_photo.values(), key=lambda x: x["score"])
#     final_filenames = [item["filename"] for item in final_items]

#     print("\n[FINAL MATCHES]")
#     for item in final_items:
#         print(
#             f"  photo={item['filename']} | cluster={item['cluster_id']}"
#             f" | final={item['score']:.4f} | conf={item['confidence']}"
#             f" | arc={item['arc_score']:.4f} | facenet={item['facenet_score']:.4f}"
#         )
#     print(f"[TOTAL] {len(final_filenames)}")

#     return {
#         "matches":        final_filenames,
#         "count":          len(final_filenames),
#         "ranked_matches": final_items,
#     }


# # -----------------------------------
# # CLUSTER SUMMARY
# # -----------------------------------
# @app.get("/cluster-summary/{event_code}")
# def cluster_summary(event_code: str):
#     records = load_event_embeddings(event_code)
#     if not records:
#         return {"event_code": event_code, "clusters": []}

#     records, clusters = assign_clusters(records)
#     save_event_embeddings(event_code, records)
#     del records
#     gc.collect()

#     summary = [
#         {
#             "cluster_id": c["cluster_id"],
#             "count":      len(c["members"]),
#             "photos":     sorted({m["filename"] for m in c["members"]}),
#         }
#         for c in clusters
#     ]
#     return {"event_code": event_code, "clusters": summary}



