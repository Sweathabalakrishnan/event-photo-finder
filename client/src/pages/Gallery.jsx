import React, { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export default function Gallery() {
  const navigate = useNavigate();
  const location = useLocation();

  const [downloading, setDownloading] = useState("");
  const [imageErrors, setImageErrors] = useState({});

  const galleryData = useMemo(() => {
    const state = location.state || {};

    return {
      matches: Array.isArray(state.matches) ? state.matches : [],
      personName: state.personName || state.name || "Guest",
      eventCode: state.eventCode || "",
      loading: Boolean(state.loading)
    };
  }, [location.state]);

  const { matches, personName, eventCode, loading } = galleryData;

  const handleBackHome = () => {
    navigate("/");
  };

  const handleView = (imageUrl) => {
    if (!imageUrl) {
      alert("Image URL not available");
      return;
    }

    window.open(imageUrl, "_blank", "noopener,noreferrer");
  };

  const handleDownload = async (imageUrl, filename) => {
    if (!imageUrl) {
      alert("Image URL not available");
      return;
    }

    try {
      setDownloading(filename || "downloading");

      const response = await fetch(imageUrl, {
        method: "GET"
      });

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
      setDownloading("");
    }
  };

  const handleImageError = (filename) => {
    setImageErrors((prev) => ({
      ...prev,
      [filename]: true
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
            marginBottom: "16px"
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

            <p className="cardText" style={{ marginBottom: "0" }}>
              Results for {personName}
              {eventCode ? ` • Event Code: ${eventCode}` : ""}
            </p>
          </div>

          <button className="btn" onClick={handleBackHome}>
            Back to Home
          </button>
        </div>

        {loading && (
          <div className="emptyState">
            <h3>Loading matched photos...</h3>
            <p>Please wait while we prepare your gallery.</p>
          </div>
        )}

        {!loading && matches.length === 0 && (
          <div className="emptyState">
            <h3>No matched photos found</h3>
            <p>
              We could not find matching images right now. Please try with
              clearer reference photos.
            </p>
          </div>
        )}

        {!loading && matches.length > 0 && (
          <div
            className="galleryGrid"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "18px"
            }}
          >
            {matches.map((photo, index) => {
              const filename =
                photo?.filename || `matched-photo-${index + 1}.jpg`;
              const imageUrl = photo?.imageUrl || "";
              const imageFailed = imageErrors[filename];

              return (
                <div
                  key={`${filename}-${index}`}
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
                      background: "#f1f5f9",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      marginBottom: "14px"
                    }}
                  >
                    {!imageFailed && imageUrl ? (
                      <img
                        src={imageUrl}
                        alt={filename}
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                          display: "block"
                        }}
                        onError={() => handleImageError(filename)}
                      />
                    ) : (
                      <div
                        style={{
                          padding: "12px",
                          textAlign: "center",
                          color: "#64748b",
                          fontSize: "14px"
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
                    {filename}
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
                      onClick={() => handleDownload(imageUrl, filename)}
                      disabled={!imageUrl || downloading === filename}
                    >
                      {downloading === filename ? "Downloading..." : "Download"}
                    </button>

                    <button
                      className="btn"
                      onClick={() => handleView(imageUrl)}
                      disabled={!imageUrl}
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
