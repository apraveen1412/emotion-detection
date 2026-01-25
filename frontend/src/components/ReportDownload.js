import React, { useState } from "react";
import { Download } from "lucide-react";

function ReportDownload({ token }) {
  const [open, setOpen] = useState(false);

  const downloadReport = async (range) => {
    try {
      const res = await fetch(
        `http://localhost:8000/report/csv?range=${range}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!res.ok) {
        alert("Failed to download report");
        return;
      }

      const data = await res.json();

      const blob = new Blob([data.content], { type: "text/csv" });
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
    }
  };

  return (
    <div className="report-dropdown">
      <button
      className="download-icon-btn"
      onClick={() => setOpen(!open)}
      title="Download Report" >
      <Download size={18} />
    </button>


      {open && (
        <div className="dropdown-menu">
          <div onClick={() => downloadReport("weekly")}>Weekly</div>
          <div onClick={() => downloadReport("monthly")}>Monthly</div>
          <div onClick={() => downloadReport("yearly")}>Yearly</div>
        </div>
      )}
    </div>
  );
}

export default ReportDownload;
