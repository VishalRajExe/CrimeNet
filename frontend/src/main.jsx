import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("CrimeNet Runtime Error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: "40px 24px",
          maxWidth: 720,
          margin: "40px auto",
          fontFamily: "system-ui, -apple-system, sans-serif",
          background: "#ffffff",
          borderRadius: 8,
          boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
          border: "1px solid #e2e8f0"
        }}>
          <h2 style={{ color: "#ef4444", marginTop: 0, fontSize: 20 }}>Application Error Encountered</h2>
          <p style={{ color: "#475569", fontSize: 13, lineHeight: 1.5 }}>
            A rendering error occurred in the network visualization component:
          </p>
          <pre style={{
            background: "#0f172a",
            color: "#f87171",
            padding: 16,
            borderRadius: 6,
            fontSize: 12,
            overflowX: "auto",
            lineHeight: 1.4,
            border: "1px solid #334155"
          }}>
            {this.state.error?.toString()}
            {"\n\n"}
            {this.state.errorInfo?.componentStack}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: 18,
              padding: "9px 20px",
              background: "#2563eb",
              color: "#ffffff",
              border: "none",
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer"
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
