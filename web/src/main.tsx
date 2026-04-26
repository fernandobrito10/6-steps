import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { LangContext, useLangState } from "./i18n";
import "./index.css";

function Root() {
  const value = useLangState();
  return (
    <LangContext.Provider value={value}>
      <App />
    </LangContext.Provider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
