import { useNavigate } from "react-router-dom";
import { useState } from "react";

export default function Home() {
  const [eventCode, setEventCode] = useState("");
  const navigate = useNavigate();

  const openEvent = () => {
    if (!eventCode.trim()) return;
    navigate(`/event/${eventCode.trim()}`);
  };

  return (
    <>
      <section className="hero">
        <div className="heroCard">
          <div>
            <h1 className="heroTitle">Find your event photos in seconds</h1>
            <p className="heroText">
              Guests scan a QR code, upload a selfie, and instantly get the photos
              in which they appear. Perfect for weddings, birthday parties, college
              functions, and corporate events.
            </p>

            <label className="label">Enter Event Code</label>
            <input
              className="input"
              placeholder="Example: AB12CD34"
              value={eventCode}
              onChange={(e) => setEventCode(e.target.value)}
            />

            <div className="btnRow">
              <button className="btn btnPrimary" onClick={openEvent}>
                Open Event
              </button>
              <button
                className="btn btnSecondary"
                onClick={() => navigate("/admin")}
              >
                Go to Admin
              </button>
            </div>
          </div>

          <div className="grid">
            <div className="statCard">
              <div className="statNumber">QR Access</div>
              <div className="statLabel">Easy sharing for guests</div>
            </div>
            <div className="statCard">
              <div className="statNumber">AI Face Match</div>
              <div className="statLabel">Personal photo retrieval</div>
            </div>
            <div className="statCard">
              <div className="statNumber">Private Gallery</div>
              <div className="statLabel">Only matched event photos</div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}