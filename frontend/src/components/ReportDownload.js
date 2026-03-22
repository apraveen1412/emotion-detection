import React, { useState } from "react";
import { Download } from "lucide-react";
import "./ReportDownload.css";
import { API_BASE } from "../utils/api";

function ReportDownload({ token }) {
  const [open, setOpen] = useState(false);

  // FIX: was a single boolean — all three buttons showed "Downloading..."
  // together. Now tracks WHICH range is loading so only that button updates.
  const [loadingRange, setLoadingRange] = useState(null);

  const downloadReport = async (range) => {
    setLoadingRange(range);
    try {
      const res = await fetch(
        `${API_BASE}/report/excel?range=${range}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (!res.ok) {
        alert("Failed to download report");
        return;
      }

      const data = await res.json();

      const byteCharacters = atob(data.content);
      const byteArray = new Uint8Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteArray[i] = byteCharacters.charCodeAt(i);
      }

      const blob = new Blob([byteArray], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = data.filename;
      a.click();
      window.URL.revokeObjectURL(url);
      setOpen(false);
    } catch (err) {
      console.error(err);
      alert("Error downloading report");
    } finally {
      setLoadingRange(null);
    }
  };

  const RANGES = ["weekly", "monthly", "yearly"];

  return (
    <div className="report-dropdown">
      <button
        className="download-icon-btn"
        onClick={() => setOpen(!open)}
        title="Download Report"
        disabled={loadingRange !== null}
      >
        <Download size={18} />
      </button>

      {open && (
        <div className="dropdown-menu">
          {RANGES.map((range) => (
            <div
              key={range}
              onClick={() => loadingRange === null && downloadReport(range)}
              style={{ opacity: loadingRange && loadingRange !== range ? 0.45 : 1 }}
            >
              {loadingRange === range
                ? `⏳ Downloading...`
                : range.charAt(0).toUpperCase() + range.slice(1)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ReportDownload;