


// import { useState } from "react";
// import { api } from "../api";
// import { QRCodeCanvas } from "qrcode.react";

// export default function Admin() {
//   const [form, setForm] = useState({
//     name: "",
//     date: "",
//     venue: ""
//   });

//   const [event, setEvent] = useState(null);
//   const [photos, setPhotos] = useState([]);
//   const [creating, setCreating] = useState(false);
//   const [uploading, setUploading] = useState(false);
//   const [message, setMessage] = useState("");
//   const [error, setError] = useState("");

//   const createEvent = async () => {
//     if (!form.name || !form.date || !form.venue) {
//       setError("Please fill in all event details.");
//       setMessage("");
//       return;
//     }

//     try {
//       setCreating(true);
//       setError("");
//       setMessage("");

//       const res = await api.post("/events/create", form);
//       setEvent(res.data);
//       setMessage("Event created successfully.");
//     } catch (err) {
//       setError(
//         err?.response?.data?.error ||
//         err?.response?.data?.details ||
//         "Failed to create event."
//       );
//       setMessage("");
//     } finally {
//       setCreating(false);
//     }
//   };

//   const handlePhotoChange = (e) => {
//     const files = Array.from(e.target.files || []);
//     setPhotos(files);
//     setError("");
//     setMessage("");
//   };

//   const uploadPhotos = async () => {
//     if (!event) {
//       setError("Create the event first.");
//       setMessage("");
//       return;
//     }

//     if (photos.length === 0) {
//       setError("Please select event photos to upload.");
//       setMessage("");
//       return;
//     }

//     try {
//       setUploading(true);
//       setError("");
//       setMessage("");

//       const fd = new FormData();
//       photos.forEach((photo) => fd.append("photos", photo));

//       const res = await api.post(`/events/${event.eventCode}/photos`, fd, {
//         headers: { "Content-Type": "multipart/form-data" }
//       });

//       setMessage(
//         `${res.data.count || photos.length} photo(s) uploaded and indexed successfully.`
//       );
//       setPhotos([]);
//     } catch (err) {
//       setError(
//         err?.response?.data?.error ||
//         err?.response?.data?.details ||
//         "Photo upload failed."
//       );
//       setMessage("");
//     } finally {
//       setUploading(false);
//     }
//   };

//   const eventUrl = event ? `http://localhost:5173/event/${event.eventCode}` : "";

//   return (
//     <section className="section">
//       <div className="grid grid2">
//         <div className="card">
//           <h2 className="cardTitle">Create Event</h2>
//           <p className="cardText">
//             Create an event and generate a unique QR-based guest access link.
//           </p>

//           <label className="label">Event Name</label>
//           <input
//             className="input"
//             type="text"
//             placeholder="Example: Sweatha Wedding Reception"
//             value={form.name}
//             onChange={(e) => setForm({ ...form, name: e.target.value })}
//           />

//           <label className="label">Event Date</label>
//           <input
//             className="input"
//             type="date"
//             value={form.date}
//             onChange={(e) => setForm({ ...form, date: e.target.value })}
//           />

//           <label className="label">Venue</label>
//           <input
//             className="input"
//             type="text"
//             placeholder="Example: ABC Mahal, Chennai"
//             value={form.venue}
//             onChange={(e) => setForm({ ...form, venue: e.target.value })}
//           />

//           <div className="btnRow">
//             <button
//               className="btn btnPrimary"
//               onClick={createEvent}
//               disabled={creating}
//             >
//               {creating ? "Creating Event..." : "Create Event"}
//             </button>
//           </div>

//           {message && (
//             <p className="statusSuccess">{message}</p>
//           )}

//           {error && (
//             <p className="statusError">{error}</p>
//           )}
//         </div>

//         <div className="card qrCard">
//           <h2 className="cardTitle">Event Access QR</h2>
//           <p className="cardText">
//             After creating the event, guests can scan this QR code to upload their selfie and find their photos.
//           </p>

//           {event ? (
//             <>
//               <QRCodeCanvas value={eventUrl} size={200} />
//               <div className="infoStrip" style={{ justifyContent: "center" }}>
//                 <span className="pill">Code: {event.eventCode}</span>
//                 <span className="pill">{event.date}</span>
//               </div>
//               <p className="cardText" style={{ wordBreak: "break-word" }}>
//                 {eventUrl}
//               </p>
//             </>
//           ) : (
//             <div className="emptyState">
//               <h3>No event created yet</h3>
//               <p>Create an event to generate the QR code and guest link.</p>
//             </div>
//           )}
//         </div>
//       </div>

//       {event && (
//         <>
//           <div className="card" style={{ marginTop: "20px" }}>
//             <div className="eventHeader">
//               <div>
//                 <h2 className="cardTitle" style={{ marginBottom: "6px" }}>
//                   {event.name}
//                 </h2>
//                 <p className="eventMeta">
//                   {event.date} • {event.venue}
//                 </p>
//               </div>

//               <div className="infoStrip">
//                 <span className="pill">Event Code: {event.eventCode}</span>
//                 <span className="pill">Admin Ready</span>
//               </div>
//             </div>
//           </div>

//           <div className="card" style={{ marginTop: "20px" }}>
//             <h2 className="cardTitle">Upload Event Photos</h2>
//             <p className="cardText">
//               Upload all event photos here. They will be indexed for AI face matching.
//             </p>

//             <div className="fileWrap">
//               <input
//                 className="fileInput"
//                 type="file"
//                 multiple
//                 accept="image/*"
//                 onChange={handlePhotoChange}
//               />
//             </div>

//             {photos.length > 0 && (
//               <>
//                 <div className="infoStrip">
//                   <span className="pill">{photos.length} file(s) selected</span>
//                 </div>

//                 <ul className="fileList">
//                   {photos.slice(0, 5).map((file, index) => (
//                     <li key={index}>{file.name}</li>
//                   ))}
//                   {photos.length > 5 && (
//                     <li>+ {photos.length - 5} more file(s)</li>
//                   )}
//                 </ul>
//               </>
//             )}

//             <div className="btnRow">
//               <button
//                 className="btn btnPrimary"
//                 onClick={uploadPhotos}
//                 disabled={uploading || photos.length === 0}
//               >
//                 {uploading ? "Uploading Photos..." : "Upload Photos"}
//               </button>
//             </div>
//           </div>
//         </>
//       )}
//     </section>
//   );
// }



import { useState } from "react";
import { api } from "../api";
import { QRCodeCanvas } from "qrcode.react";

export default function Admin() {
  const [form, setForm] = useState({
    name: "",
    date: "",
    venue: ""
  });

  const [event, setEvent] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [indexSummary, setIndexSummary] = useState(null);

  const createEvent = async () => {
    if (!form.name || !form.date || !form.venue) {
      setError("Please fill in all event details.");
      setMessage("");
      return;
    }

    try {
      setCreating(true);
      setError("");
      setMessage("");
      setIndexSummary(null);

      const res = await api.post("/events/create", form);
      setEvent(res.data);
      setMessage("Event created successfully.");
    } catch (err) {
      setError(
        err?.response?.data?.error ||
          err?.response?.data?.details ||
          "Failed to create event."
      );
      setMessage("");
    } finally {
      setCreating(false);
    }
  };

  const handlePhotoChange = (e) => {
    const files = Array.from(e.target.files || []);
    setPhotos(files);
    setError("");
    setMessage("");
  };

  const uploadPhotos = async () => {
    if (!event) {
      setError("Create the event first.");
      setMessage("");
      return;
    }

    if (photos.length === 0) {
      setError("Please select event photos to upload.");
      setMessage("");
      return;
    }

    try {
      setUploading(true);
      setError("");
      setMessage("");
      setIndexSummary(null);

      const fd = new FormData();
      photos.forEach((photo) => fd.append("photos", photo));

      const res = await api.post(`/events/${event.eventCode}/photos`, fd, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      setMessage("Photo upload and indexing completed.");
      setIndexSummary(res.data);
      setPhotos([]);
    } catch (err) {
      setError(
        err?.response?.data?.error ||
          err?.response?.data?.details ||
          "Photo upload failed."
      );
      setMessage("");
    } finally {
      setUploading(false);
    }
  };

  const eventUrl = event ? `http://localhost:5173/event/${event.eventCode}` : "";

  return (
    <section className="section">
      <div className="grid grid2">
        <div className="card">
          <h2 className="cardTitle">Create Event</h2>
          <p className="cardText">
            Create an event and generate a guest access QR code.
          </p>

          <label className="label">Event Name</label>
          <input
            className="input"
            type="text"
            placeholder="Example: Birthday Party"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />

          <label className="label">Event Date</label>
          <input
            className="input"
            type="date"
            value={form.date}
            onChange={(e) => setForm({ ...form, date: e.target.value })}
          />

          <label className="label">Venue</label>
          <input
            className="input"
            type="text"
            placeholder="Example: ABC Hall"
            value={form.venue}
            onChange={(e) => setForm({ ...form, venue: e.target.value })}
          />

          <div className="btnRow">
            <button
              className="btn btnPrimary"
              onClick={createEvent}
              disabled={creating}
            >
              {creating ? "Creating Event..." : "Create Event"}
            </button>
          </div>

          {message && <p className="statusSuccess">{message}</p>}
          {error && <p className="statusError">{error}</p>}
        </div>

        <div className="card qrCard">
          <h2 className="cardTitle">Event Access QR</h2>
          <p className="cardText">
            Guests can scan this QR code and upload 2–3 reference photos.
          </p>

          {event ? (
            <>
              <QRCodeCanvas value={eventUrl} size={200} />
              <div className="infoStrip" style={{ justifyContent: "center" }}>
                <span className="pill">Code: {event.eventCode}</span>
                <span className="pill">{event.date}</span>
              </div>
              <p className="cardText" style={{ wordBreak: "break-word" }}>
                {eventUrl}
              </p>
            </>
          ) : (
            <div className="emptyState">
              <h3>No event created yet</h3>
              <p>Create an event to generate the QR code and guest link.</p>
            </div>
          )}
        </div>
      </div>

      {event && (
        <>
          <div className="card" style={{ marginTop: "20px" }}>
            <div className="eventHeader">
              <div>
                <h2 className="cardTitle" style={{ marginBottom: "6px" }}>
                  {event.name}
                </h2>
                <p className="eventMeta">
                  {event.date} • {event.venue}
                </p>
              </div>

              <div className="infoStrip">
                <span className="pill">Event Code: {event.eventCode}</span>
                <span className="pill">Admin Ready</span>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: "20px" }}>
            <h2 className="cardTitle">Upload Event Photos</h2>
            <p className="cardText">
              Upload event images. The system will index faces from each photo.
            </p>

            <div className="fileWrap">
              <input
                className="fileInput"
                type="file"
                multiple
                accept="image/*"
                onChange={handlePhotoChange}
              />
            </div>

            {photos.length > 0 && (
              <>
                <div className="infoStrip">
                  <span className="pill">{photos.length} file(s) selected</span>
                </div>

                <ul className="fileList">
                  {photos.slice(0, 5).map((file, index) => (
                    <li key={index}>{file.name}</li>
                  ))}
                  {photos.length > 5 && (
                    <li>+ {photos.length - 5} more file(s)</li>
                  )}
                </ul>
              </>
            )}

            <div className="btnRow">
              <button
                className="btn btnPrimary"
                onClick={uploadPhotos}
                disabled={uploading || photos.length === 0}
              >
                {uploading ? "Uploading Photos..." : "Upload Photos"}
              </button>
            </div>
          </div>

          {indexSummary && (
            <div className="card" style={{ marginTop: "20px" }}>
              <h2 className="cardTitle">Indexing Summary</h2>

              <div className="infoStrip">
                <span className="pill">
                  Total: {indexSummary.totalUploaded ?? 0}
                </span>
                <span className="pill">
                  Success: {indexSummary.successCount ?? 0}
                </span>
                <span className="pill">
                  Failed: {indexSummary.failedCount ?? 0}
                </span>
              </div>

              {indexSummary.failed?.length > 0 && (
                <>
                  <h3 style={{ marginTop: "18px" }}>Failed Files</h3>
                  <ul className="fileList">
                    {indexSummary.failed.map((item, idx) => (
                      <li key={idx}>
                        <strong>{item.filename}</strong> — {item.error}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}