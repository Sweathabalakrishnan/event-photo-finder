

import { useLocation, Link } from "react-router-dom";

export default function Gallery() {
  const location = useLocation();
  const matches = location.state?.matches || [];
  const event = location.state?.event;

  const downloadImage = async (url, filename) => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename || "photo.jpg";
      document.body.appendChild(a);
      a.click();
      a.remove();

      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      alert("Download failed");
    }
  };

  return (
    <section className="section">
      <div className="card">
        <div className="eventHeader">
          <div>
            <h1 className="cardTitle" style={{ fontSize: "2rem" }}>
              Your Matched Photos
            </h1>
            <p className="cardText">
              {event?.name ? `Results for ${event.name}` : "Matched event photos"}
            </p>
          </div>

          <Link className="btn btnSecondary" to="/">
            Back to Home
          </Link>
        </div>

        {matches.length === 0 ? (
          <div className="emptyState">
            <h3>No matched photos found</h3>
            <p>Try uploading clearer reference photos or better event images.</p>
          </div>
        ) : (
          <div className="photoGrid">
            {matches.map((photo, index) => (
              <div className="photoCard" key={index}>
                <img
                  className="photoPreview"
                  src={photo.imageUrl}
                  alt={photo.filename}
                  onError={(e) => {
                    e.currentTarget.style.display = "none";
                  }}
                />
                <div className="photoBody">
                  <div className="photoName">{photo.filename}</div>

                  <div className="btnRow">
                    <button
                      className="btn btnPrimary"
                      onClick={() => downloadImage(photo.imageUrl, photo.filename)}
                    >
                      Download
                    </button>

                    <a
                      className="btn btnSecondary"
                      href={photo.imageUrl}
                      target="_blank"
                      rel="noreferrer"
                    >
                      View
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
