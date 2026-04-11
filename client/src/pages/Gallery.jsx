import React, { useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

function getBackendBaseUrl() {
  const apiUrl = import.meta.env.VITE_API_URL || "";

  if (apiUrl.endsWith("/api")) {
    return apiUrl.replace("/api", "");
  }

  return apiUrl;
}

function normalizeMatchItem(item, eventCode, backendBaseUrl, index) {
  let filename = "";
  let imageUrl = "";

  if (typeof item === "string") {
    filename = item;
  } else if (item && typeof item === "object") {
    filename = item.filename || item.name || `photo-${index}.jpg`;
    imageUrl = item.imageUrl || item.url || "";
  }

  // localhost URL வந்தா production backend URL-ஆ மாற்று
 if (imageUrl.startsWith("http://localhost")) {
  imageUrl = imageUrl.replace("http://localhost:5000", backendBaseUrl);
}

  if (!imageUrl && filename && backendBaseUrl && eventCode) {
    imageUrl = `${backendBaseUrl}/uploads/events/${eventCode}/${encodeURIComponent(
      filename
    )}`;
  }

  return {
    id: `${filename}-${index}`,
    filename,
    imageUrl
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

    window.open(imageUrl, "_blank", "noopener,noreferrer");
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
        throw new Error(`Failed to fetch image (${response.status})`);
      }

      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename || "matched-photo.jpg";
      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      console.error("Download failed:", error);
      alert("Download failed. Please try again.");
    } finally {
      setDownloadingId("");
    }
  };

  const onImageError = (id) => {
    setImageErrors((prev) => ({
      ...prev,
      [id]: true
    }));
  };

  return (
    <section className="section">
      <div className="card">
        <div
          className="eventHeader"
          style={{
            alignItems: "center",
            justifyContent: "space-between",
            gap: "12px",
            marginBottom: "18px"
          }}
        >
          <div>
            <h1
              className="cardTitle"
              style={{
                fontSize: "clamp(2rem, 4vw, 3rem)",
                marginBottom: "10px"
              }}
            >
              Your Matched Photos
            </h1>

            <p className="cardText" style={{ marginBottom: 0 }}>
              Results for {personName}
            </p>
          </div>

          <button className="btn" onClick={handleBackHome}>
            Back to Home
          </button>
        </div>

        {matches.length === 0 ? (
          <div className="emptyState">
            <h3>No matched photos found</h3>
            <p>Please try again with clearer reference photos.</p>
          </div>
        ) : (
          <div
            className="galleryGrid"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "18px"
            }}
          >
            {matches.map((photo) => {
              const imageFailed = imageErrors[photo.id];

              return (
                <div
                  key={photo.id}
                  className="galleryCard"
                  style={{
                    border: "1px solid #dbe3ee",
                    borderRadius: "18px",
                    padding: "14px",
                    background: "#ffffff",
                    boxShadow: "0 8px 20px rgba(15, 23, 42, 0.05)"
                  }}
                >
                  <div
                    style={{
                      width: "100%",
                      height: "180px",
                      borderRadius: "14px",
                      overflow: "hidden",
                      background: "#eef2f7",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      marginBottom: "14px"
                    }}
                  >
                    {!imageFailed && photo.imageUrl ? (
                      <img
                        src={photo.imageUrl}
                        alt={photo.filename}
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                          display: "block"
                        }}
                        onError={() => onImageError(photo.id)}
                      />
                    ) : (
                      <div
                        style={{
                          textAlign: "center",
                          color: "#64748b",
                          fontSize: "14px",
                          padding: "10px"
                        }}
                      >
                        Image preview not available
                      </div>
                    )}
                  </div>

                  <p
                    style={{
                      fontWeight: 700,
                      color: "#0f172a",
                      fontSize: "15px",
                      lineHeight: 1.5,
                      wordBreak: "break-word",
                      marginBottom: "14px",
                      minHeight: "48px"
                    }}
                  >
                    {photo.filename}
                  </p>

                  <div
                    className="btnRow"
                    style={{
                      display: "flex",
                      gap: "10px",
                      flexWrap: "wrap"
                    }}
                  >
                    <button
                      className="btn btnPrimary"
                      onClick={() =>
                        handleDownload(photo.imageUrl, photo.filename, photo.id)
                      }
                      disabled={!photo.imageUrl || downloadingId === photo.id}
                    >
                      {downloadingId === photo.id ? "Downloading..." : "Download"}
                    </button>

                    <button
                      className="btn"
                      onClick={() => handleView(photo.imageUrl)}
                      disabled={!photo.imageUrl}
                    >
                      View
                    </button>
                  </div>
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
