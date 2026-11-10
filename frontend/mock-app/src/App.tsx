import { useEffect, useState } from "react";

type HealthResponse = {
  status: string;
};

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`);
        }
        return response.json() as Promise<HealthResponse>;
      })
      .then(setHealth)
      .catch((requestError: Error) => setError(requestError.message));
  }, []);

  return (
    <main>
      <h1>TP-Topicos2</h1>
      <p>
        Backend:{" "}
        {health ? health.status : error ? `error (${error})` : "conectando..."}
      </p>
    </main>
  );
}
