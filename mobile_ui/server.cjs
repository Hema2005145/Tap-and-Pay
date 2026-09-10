const http = require("http");
const { Server } = require("socket.io");

const httpServer = http.createServer((req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    res.writeHead(200);
    res.end();
    return;
  }

  if (req.method === "POST" && (req.url === "/emit" || req.url === "/api/quic-event")) {
    let body = "";
    req.on("data", (chunk) => { body += chunk; });
    req.on("end", () => {
      try {
        const payload = JSON.parse(body || "{}");
        const eventName = payload.event || "quic_event";
        const eventData = payload.data !== undefined ? payload.data : payload;
        
        io.emit(eventName, eventData);
        console.log(`[Relay] Broadcasted '${eventName}' -> Stage: ${eventData?.stage || 'N/A'}, Status: ${eventData?.status || 'N/A'}`);

        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ status: "success", broadcast: eventName }));
      } catch (err) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ status: "error", message: err.message }));
      }
    });
    return;
  }

  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", service: "QSP3 WebSocket Relay" }));
    return;
  }

  res.writeHead(404);
  res.end();
});

const io = new Server(httpServer, {
  cors: {
    origin: "*", // allow all connections
  }
});

io.on("connection", (socket) => {
  console.log(`[Socket] Device connected: ${socket.id}`);

  socket.on("payment_sent", (data) => {
    console.log(`[Socket] Payment received from Sender: $${data.amount}. Forcing Global Broadcast...`);
    // Force a global emit to ALL connected devices (including sender) to bypass strict NAT/Firewall routing rules
    io.emit("payment_received", data);
  });

  socket.on("quic_event_forward", (data) => {
    // Allows clients to forward verified quic events
    io.emit("quic_event", data);
  });

  socket.on("disconnect", () => {
    console.log(`[Socket] Device disconnected: ${socket.id}`);
  });
});

console.log("WebSocket server running on port 3001...");
const PORT = 3001;
httpServer.listen(PORT, "0.0.0.0", () => {
  console.log(`WebSocket server & Event Relay running on port ${PORT}...`);
});

