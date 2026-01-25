import React from "react";
import { Line } from "react-chartjs-2";
import "chart.js/auto";

/* -------------------------------------------------
   SCIENTIFICALLY MAPPED EMOTION COLORS (GoEmotions)
------------------------------------------------- */
const EMOTION_COLORS = {
  joy: "#FFD166",
  amusement: "#FFC857",
  excitement: "#FF9F1C",
  gratitude: "#6BCF63",
  love: "#F77F9A",
  admiration: "#4ECDC4",
  pride: "#5BC0EB",
  optimism: "#A7E163",
  relief: "#9AE6B4",

  anger: "#D62828",
  annoyance: "#E76F51",
  disgust: "#6A994E",
  fear: "#5A189A",
  nervousness: "#7B2CBF",

  sadness: "#457B9D",
  grief: "#2C3E50",
  disappointment: "#6C757D",
  remorse: "#5F6CAF",
  embarrassment: "#B56576",

  confusion: "#8D99AE",
  curiosity: "#48CAE4",
  realization: "#4D96FF",
  surprise: "#56CFE1",
  neutral: "#ADB5BD",

  caring: "#52B788",
  approval: "#74C69D",
  disapproval: "#8B0000",
  desire: "#FF758F",
};

const getColor = (emotion) => EMOTION_COLORS[emotion] || "#9CA3AF";

/* =================================================
   EMOTION TIMELINE (MULTI-LABEL, SCORE-FREE)
================================================= */

function EmotionTimeline({ history }) {
  /* ---------- SAFETY CHECK ---------- */
  if (!Array.isArray(history) || history.length === 0) {
    return <p style={{ textAlign: "center" }}>No emotion data yet.</p>;
  }

  /* ---------- X-AXIS DATES ---------- */
  const labels = history.map((h) => h.date);

  /* ---------- ALL EMOTIONS THAT EVER APPEARED ---------- */
  const emotionSet = new Set();
  history.forEach((h) => {
    if (Array.isArray(h.emotions)) {
      h.emotions.forEach((e) => emotionSet.add(e));
    }
  });

  const emotions = Array.from(emotionSet);

  /* ---------- DATASETS (PRESENCE-BASED) ---------- */
  const datasets = emotions.map((emotion) => ({
    label: emotion,
    data: history.map((h) =>
      Array.isArray(h.emotions) && h.emotions.includes(emotion)
        ? 1
        : null
    ),
    borderColor: getColor(emotion),
    backgroundColor: getColor(emotion),
    pointRadius: 6,
    pointHoverRadius: 8,
    showLine: false, // dots only → avoids false continuity
  }));

  const data = { labels, datasets };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top",
        labels: {
          usePointStyle: true,
        },
      },
      tooltip: {
        callbacks: {
          label: (ctx) => `Emotion: ${ctx.dataset.label}`,
        },
      },
    },
    scales: {
      y: {
        display: false, // categorical presence only
      },
      x: {
        grid: { display: false },
      },
    },
  };

  return (
    <div style={{ height: "260px" }}>
      <Line data={data} options={options} />
    </div>
  );
}

export default EmotionTimeline;
