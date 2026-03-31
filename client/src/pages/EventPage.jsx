// import { useEffect, useMemo, useState } from "react";
// import { useNavigate, useParams } from "react-router-dom";
// import { api } from "../api";

// export default function EventPage() {
//   const { eventCode } = useParams();
//   const navigate = useNavigate();

//   const [event, setEvent] = useState(null);
//   const [selfie, setSelfie] = useState(null);
//   const [preview, setPreview] = useState("");
//   const [loading, setLoading] = useState(false);
//   const [fetchingEvent, setFetchingEvent] = useState(true);
//   const [error, setError] = useState("");

//   useEffect(() => {
//     const loadEvent = async () => {
//       try {
//         setFetchingEvent(true);
//         setError("");
//         const res = await api.get(`/events/${eventCode}`);
//         setEvent(res.data);
//       } catch (err) {
//         setError(err?.response?.data?.error || "Unable to load event details.");
//       } finally {
//         setFetchingEvent(false);
//       }
//     };

//     loadEvent();
//   }, [eventCode]);

//   const previewUrl = useMemo(() => preview, [preview]);

//   const handleSelfieChange = (e) => {
//     const file = e.target.files?.[0];
//     if (!file) return;

//     setSelfie(file);
//     setPreview(URL.createObjectURL(file));
//     setError("");
//   };

//   const findPhotos = async () => {
//     if (!selfie) {
//       setError("Please upload a selfie first.");
//       return;
//     }

//     try {
//       setLoading(true);
//       setError("");

//       const fd = new FormData();
//       fd.append("selfie", selfie);

//       const res = await api.post(`/events/${eventCode}/match`, fd, {
//         headers: {
//           "Content-Type": "multipart/form-data"
//         }
//       });

//       navigate("/gallery", {
//         state: {
//           matches: res.data.matches || [],
//           event
//         }
//       });
//     } catch (err) {
//       setError(err?.response?.data?.error || "Photo matching failed.");
//     } finally {
//       setLoading(false);
//     }
//   };

//   if (fetchingEvent) {
//     return (
//       <section className="section">
//         <div className="card">
//           <div className="loaderBox">
//             <div className="spinner"></div>
//             <p className="cardText">Loading event details...</p>
//           </div>
//         </div>
//       </section>
//     );
//   }

//   if (error && !event) {
//     return (
//       <section className="section">
//         <div className="card">
//           <h2 className="cardTitle">Event not found</h2>
//           <p className="cardText">{error}</p>
//         </div>
//       </section>
//     );
//   }

//   return (
//     <section className="section">
//       <div className="card">
//         <div className="eventHeader">
//           <div>
//             <h1 className="eventTitle">{event?.name}</h1>
//             <p className="eventMeta">
//               {event?.date} • {event?.venue}
//             </p>

//             <div className="infoStrip">
//               <span className="pill">Event Code: {event?.eventCode}</span>
//               <span className="pill">Selfie Match Enabled</span>
//             </div>
//           </div>

//           <div className="card qrCard" style={{ minWidth: "240px", margin: 0 }}>
//             <h3 className="cardTitle" style={{ marginBottom: 0 }}>Guest Access</h3>
//             <p className="cardText" style={{ marginBottom: 0 }}>
//               Upload a clear selfie to find your event photos instantly.
//             </p>
//           </div>
//         </div>
//       </div>

//       <div className="grid grid2">
//         <div className="card">
//           <h2 className="cardTitle">Upload Your Selfie</h2>
//           <p className="cardText">
//             Use a front-facing, clear selfie for better matching accuracy.
//           </p>

//           <div className="fileWrap">
//             <input
//               className="fileInput"
//               type="file"
//               accept="image/*"
//               onChange={handleSelfieChange}
//             />
//           </div>

//           {selfie && (
//             <div className="infoStrip">
//               <span className="pill">Selected: {selfie.name}</span>
//             </div>
//           )}

//           <div className="btnRow">
//             <button
//               className="btn btnPrimary"
//               onClick={findPhotos}
//               disabled={loading}
//             >
//               {loading ? "Finding Your Photos..." : "Find My Photos"}
//             </button>
//           </div>

//           {error && (
//             <p style={{ color: "#dc2626", marginTop: "14px", fontWeight: 600 }}>
//               {error}
//             </p>
//           )}
//         </div>

//         <div className="card">
//           <h2 className="cardTitle">Selfie Preview</h2>
//           <p className="cardText">
//             Preview the uploaded image before running AI matching.
//           </p>

//           {previewUrl ? (
//             <div className="photoCard">
//               <img
//                 src={previewUrl}
//                 alt="Selfie preview"
//                 className="photoPreview"
//                 style={{ height: "320px" }}
//               />
//             </div>
//           ) : (
//             <div className="emptyState">
//               <h3>No selfie selected</h3>
//               <p>Your uploaded selfie preview will appear here.</p>
//             </div>
//           )}
//         </div>
//       </div>

//       <div className="card" style={{ marginTop: "20px" }}>
//         <h2 className="cardTitle">Tips for Best Matching</h2>
//         <div className="grid grid3">
//           <div className="statCard">
//             <div className="statNumber">Clear Face</div>
//             <div className="statLabel">Avoid blur and side-angle selfies.</div>
//           </div>
//           <div className="statCard">
//             <div className="statNumber">Good Light</div>
//             <div className="statLabel">Upload a bright and well-lit image.</div>
//           </div>
//           <div className="statCard">
//             <div className="statNumber">Single Face</div>
//             <div className="statLabel">Use a selfie with only your face visible.</div>
//           </div>
//         </div>
//       </div>
//     </section>
//   );
// }




import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";

export default function EventPage() {
  const { eventCode } = useParams();
  const navigate = useNavigate();

  const [event, setEvent] = useState(null);
  const [referencePhotos, setReferencePhotos] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [fetchingEvent, setFetchingEvent] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadEvent = async () => {
      try {
        setFetchingEvent(true);
        setError("");
        const res = await api.get(`/events/${eventCode}`);
        setEvent(res.data);
      } catch (err) {
        setError(err?.response?.data?.error || "Unable to load event.");
      } finally {
        setFetchingEvent(false);
      }
    };

    loadEvent();
  }, [eventCode]);

  const handleReferenceChange = (e) => {
    const files = Array.from(e.target.files || []);

    if (files.length > 3) {
      setError("Please upload maximum 3 photos only.");
      return;
    }

    setReferencePhotos(files);
    setError("");

    const urls = files.map((file) => URL.createObjectURL(file));
    setPreviews(urls);
  };

  const findPhotos = async () => {
    if (referencePhotos.length < 2) {
      setError("Please upload at least 2 photos for better accuracy.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const fd = new FormData();
      referencePhotos.forEach((file) => {
        fd.append("selfies", file);
      });

      const res = await api.post(`/events/${eventCode}/match`, fd, {
        headers: {
          "Content-Type": "multipart/form-data"
        }
      });

      navigate("/gallery", {
        state: {
          matches: res.data.matches || [],
          event
        }
      });
    } catch (err) {
      setError(
        err?.response?.data?.error ||
          err?.response?.data?.details ||
          "Matching failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  if (fetchingEvent) {
    return (
      <section className="section">
        <div className="card">
          <div className="loaderBox">
            <div className="spinner"></div>
            <p className="cardText">Loading event details...</p>
          </div>
        </div>
      </section>
    );
  }

  if (!event) {
    return (
      <section className="section">
        <div className="card">
          <h2 className="cardTitle">Event not found</h2>
          <p className="cardText">{error || "This event does not exist."}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="section">
      <div className="card">
        <div className="eventHeader">
          <div>
            <h1 className="eventTitle">{event.name}</h1>
            <p className="eventMeta">
              {event.date} • {event.venue}
            </p>

            <div className="infoStrip">
              <span className="pill">Event Code: {event.eventCode}</span>
              <span className="pill">AI Face Matching</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid2">
        <div className="card">
          <h2 className="cardTitle">Upload 2–3 Clear Photos</h2>
          <p className="cardText">
            Upload 2 or 3 clear photos of yourself for better matching accuracy in
            solo and group photos.
          </p>

          <div className="fileWrap">
            <input
              className="fileInput"
              type="file"
              accept="image/*"
              multiple
              onChange={handleReferenceChange}
            />
          </div>

          {referencePhotos.length > 0 && (
            <div className="infoStrip">
              <span className="pill">{referencePhotos.length} photo(s) selected</span>
            </div>
          )}

          <div className="btnRow">
            <button
              className="btn btnPrimary"
              onClick={findPhotos}
              disabled={loading || referencePhotos.length < 2}
            >
              {loading ? "Finding your photos..." : "Find My Photos"}
            </button>
          </div>

          {error && <p className="statusError">{error}</p>}
        </div>

        <div className="card">
          <h2 className="cardTitle">Reference Photo Preview</h2>
          <p className="cardText">
            Use front-facing, clear images with slightly different angles if possible.
          </p>

          {previews.length > 0 ? (
            <div className="photoGrid">
              {previews.map((src, index) => (
                <div className="photoCard" key={index}>
                  <img
                    src={src}
                    alt={`Reference ${index + 1}`}
                    className="photoPreview"
                    style={{ height: "220px" }}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="emptyState">
              <h3>No photos selected</h3>
              <p>Your uploaded reference photos will appear here.</p>
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: "20px" }}>
        <h2 className="cardTitle">Tips for best results</h2>
        <div className="grid grid3">
          <div className="statCard">
            <div className="statNumber">2–3 photos</div>
            <div className="statLabel">
              Use more than one photo for better identity matching.
            </div>
          </div>
          <div className="statCard">
            <div className="statNumber">Good lighting</div>
            <div className="statLabel">Use bright and clear face images.</div>
          </div>
          <div className="statCard">
            <div className="statNumber">Clear face</div>
            <div className="statLabel">
              Avoid blur, heavy angle, or covered face.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}