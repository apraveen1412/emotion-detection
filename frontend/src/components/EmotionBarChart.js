import React from "react";
import { Bar } from "react-chartjs-2";
import "chart.js/auto";
import "./EmotionBarChart.css";

const EMOTION_COLORS = {
  joy: "#FFD166", amusement: "#FFC857", excitement: "#FF9F1C", gratitude: "#6BCF63",
  love: "#F77F9A", admiration: "#4ECDC4", pride: "#5BC0EB", optimism: "#A7E163",
  relief: "#9AE6B4", anger: "#D62828", annoyance: "#E76F51", disgust: "#6A994E",
  fear: "#5A189A", nervousness: "#7B2CBF", sadness: "#457B9D", grief: "#2C3E50",
  disappointment: "#6C757D", remorse: "#5F6CAF", embarrassment: "#B56576",
  confusion: "#8D99AE", curiosity: "#48CAE4", realization: "#4D96FF",
  surprise: "#56CFE1", neutral: "#ADB5BD", caring: "#52B788", approval: "#74C69D",
  disapproval: "#8B0000", desire: "#FF758F",
};

const getColor = (emotion) => EMOTION_COLORS[emotion] || "#9CA3AF";

function EmotionTimeline({ history }) {
  if (!Array.isArray(history) || history.length === 0) {
    return <p style={{ textAlign: "center" }}>No emotion data yet.</p>;
  }

  // Aggregate total emotion counts across the history
  const emotionCounts = {};
  history.forEach((h) => {
    if (Array.isArray(h.emotions)) {
      h.emotions.forEach((e) => {
        emotionCounts[e] = (emotionCounts[e] || 0) + 1;
      });
    }
  });

  const labels = Object.keys(emotionCounts);
  const dataValues = Object.values(emotionCounts);
  const backgroundColors = labels.map(getColor);

  const data = {
    labels: labels,
    datasets: [
      {
        label: "Emotion Frequency",
        data: dataValues,
        backgroundColor: backgroundColors,
        borderRadius: 4,
      },
    ],
  };

  const options = {
  responsive: true,
  maintainAspectRatio: false,

  plugins: {
    legend: { display: false },

    tooltip: {
      backgroundColor: "#111827",
      padding: 10,
      titleFont: { size: 14 },
      bodyFont: { size: 13 }
    }
  },

  scales: {

    x: {
      grid: { display: false },
      ticks: {
        color: "#374151",
        font: { size: 12 }
      }
    },

    y: {
      beginAtZero: true,
      ticks: {
        stepSize: 1,
        color: "#6b7280"
      },

      grid: {
        color: "rgba(0,0,0,0.05)"
      }
    }
  }
};

  return (
    <div style={{ height: "260px" }}>
      <Bar data={data} options={options} />
    </div>
  );
}

export default EmotionTimeline;