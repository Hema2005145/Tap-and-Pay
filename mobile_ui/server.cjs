const { Server } = require("socket.io");

const io = new Server(3001, {
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

  socket.on("disconnect", () => {
    console.log(`[Socket] Device disconnected: ${socket.id}`);
  });
});

console.log("WebSocket server running on port 3001...");
