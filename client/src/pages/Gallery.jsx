import React, { useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

function getBackendBaseUrl() {
  const apiUrl = import.meta.env.VITE_API_URL || "";

  // remove /api if exists
  if (apiUrl.endsWith("/api")) {
    return apiUrl.replace("/api", "");
  }

  return apiUrl;
}

function normalizeMatchItem(item, eventCode, backendBaseUrl, index) {
  let filename = "";
  let imageUrl = "";

  // CASE 1: string
  if (typeof item === "string") {
    filename = item;
  }

  // CASE 2: object
  else if (item && typeof item === "object") {
    filename = item.filename || item.name || `photo-${index}.jpg`;
    imageUrl = item.imageUrl || item.url || "";
  }

  // BUILD IMAGE URL if missing
  if (!imageUrl && filename && backendBaseUrl && eventCode) {
    imageUrl = `${backendBaseUrl}/uploads/events/${eventCode}/${encodeURIComponent(
      filename
    )}`;
  }

  console.log("🖼️ IMAGE URL:", imageUrl); // DEBUG

  return {
    id: `${filename}-${index}`,
    filename,
    imageUrl,
  };
}

export default function Gallery() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const [downloadingId, setDownloadingId] = useState("");
  const [imageErrors, setImageErrors] = useState({});

  const backendBaseUrl = getBackendBaseUrl();

  const state = location.state || {};

  const personName =
    state.personName ||
    searchParams.get("name") ||
    "Guest";

  const eventCode =
    state.eventCode ||
    searchParams.get("eventCode") ||
    "";

  const rawMatches = Array.isArray(state.matches) ? state.matches : [];

  const matches = useMemo(() => {
    return rawMatches.map((item, index) =>
      normalizeMatchItem(item, eventCode, backendBaseUrl, index)
    );
  }, [rawMatches, eventCode, backendBaseUrl]);

  const handleBackHome = () => {
    navigate("/");
  };

  const handleView = (imageUrl) => {
    if (!imageUrl) {
      alert("Image URL not available.");
      return;
    }

    window.open(imageUrl, "_blank");
  };

  const handleDownload = async (imageUrl, filename, id) => {
    if (!imageUrl) {
      alert("Image URL not available.");
      return;
    }

    try {
      setDownloadingId(id);

      const response = await fetch(imageUrl);

      if (!response.ok) {
        throw new Error("Download failed");
      }

      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename;
      link.click();

      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error(err);
      alert("Download failed");
    } finally {
      setDownloadingId("");
    }
  };

  const onImageError = (id) => {
    setImageErrors((prev) => ({
      ...prev,
      [id]: true,
    }));
  };

  return (
    <section className="section">
      <div className="card">

        <div className="eventHeader" style={{ display: "flex", justifyContent: "space-between" }}>
          <div>
            <h1 className="cardTitle">Your Matched Photos</h1>
            <p className="cardText">Results for {personName}</p>
          </div>

          <button className="btn" onClick={handleBackHome}>
            Back to Home
          </button>
        </div>

        {matches.length === 0 ? (
          <div className="emptyState">
            <h3>No matched photos found</h3>
          </div>
        ) : (
          <div className="galleryGrid" style={{ display: "grid", gap: "16px" }}>
            {matches.map((photo) => {
              const failed = imageErrors[photo.id];

              return (
                <div key={photo.id} className="galleryCard">

                  <div style={{ height: "180px", background: "#eee" }}>
                    {!failed && photo.imageUrl ? (
                      <img
                        src={photo.imageUrl}
                        alt={photo.filename}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        onError={() => onImageError(photo.id)}
                      />
                    ) : (
                      <div>Image preview not available</div>
                    )}
                  </div>

                  <p>{photo.filename}</p>

                  <button
                    onClick={() =>
                      handleDownload(photo.imageUrl, photo.filename, photo.id)
                    }
                  >
                    Download
                  </button>

                  <button onClick={() => handleView(photo.imageUrl)}>
                    View
                  </button>

                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

// import { useLocation, Link } from "react-router-dom";

// export default function Gallery() {
//   const location = useLocation();
//   const matches = location.state?.matches || [];
//   const event = location.state?.event;

//   const downloadImage = async (url, filename) => {
//     try {
//       const response = await fetch(url);
//       const blob = await response.blob();
//       const blobUrl = window.URL.createObjectURL(blob);

//       const a = document.createElement("a");
//       a.href = blobUrl;
//       a.download = filename || "photo.jpg";
//       document.body.appendChild(a);
//       a.click();
//       a.remove();

//       window.URL.revokeObjectURL(blobUrl);
//     } catch (error) {
//       alert("Download failed");
//     }
//   };

//   return (
//     <section className="section">
//       <div className="card">
//         <div className="eventHeader">
//           <div>
//             <h1 className="cardTitle" style={{ fontSize: "2rem" }}>
//               Your Matched Photos
//             </h1>
//             <p className="cardText">
//               {event?.name ? `Results for ${event.name}` : "Matched event photos"}
//             </p>
//           </div>

//           <Link className="btn btnSecondary" to="/">
//             Back to Home
//           </Link>
//         </div>

//         {matches.length === 0 ? (
//           <div className="emptyState">
//             <h3>No matched photos found</h3>
//             <p>Try uploading clearer reference photos or better event images.</p>
//           </div>
//         ) : (
//           <div className="photoGrid">
//             {matches.map((photo, index) => (
//               <div className="photoCard" key={index}>
//                 <img
//                   className="photoPreview"
//                   src={photo.imageUrl}
//                   alt={photo.filename}
//                   onError={(e) => {
//                     e.currentTarget.style.display = "none";
//                   }}
//                 />
//                 <div className="photoBody">
//                   <div className="photoName">{photo.filename}</div>

//                   <div className="btnRow">
//                     <button
//                       className="btn btnPrimary"
//                       onClick={() => downloadImage(photo.imageUrl, photo.filename)}
//                     >
//                       Download
//                     </button>

//                     <a
//                       className="btn btnSecondary"
//                       href={photo.imageUrl}
//                       target="_blank"
//                       rel="noreferrer"
//                     >
//                       View
//                     </a>
//                   </div>
//                 </div>
//               </div>
//             ))}
//           </div>
//         )}
//       </div>
//     </section>
//   );
// }
