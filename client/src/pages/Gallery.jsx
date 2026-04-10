import React from "react";

export default function Gallery({ matches = [], personName = "" }) {
  async function handleDownload(imageUrl, filename) {
    try {
      const response = await fetch(imageUrl);
      if (!response.ok) {
        throw new Error("Failed to fetch image");
      }

      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename || "image.jpg";
      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      console.error("Download failed:", error);
      alert("Download failed");
    }
  }

  function handleView(imageUrl) {
    window.open(imageUrl, "_blank", "noopener,noreferrer");
  }

  return (
    <section className="section">
      <div className="card">
        <h1 className="pageTitle">Your Matched Photos</h1>
        <p className="cardText">Results for {personName}</p>

        <div className="gallery-grid">
          {matches.map((photo, index) => (
            <div key={index} className="gallery-card">
              <img
                src={photo.imageUrl}
                alt={photo.filename}
                className="gallery-image"
              />

              <p className="gallery-name">{photo.filename}</p>

              <div className="btnRow">
                <button
                  className="btn btnPrimary"
                  onClick={() => handleDownload(photo.imageUrl, photo.filename)}
                >
                  Download
                </button>

                <button
                  className="btn"
                  onClick={() => handleView(photo.imageUrl)}
                >
                  View
                </button>
              </div>
            </div>
          ))}
        </div>
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
