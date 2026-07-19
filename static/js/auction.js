// Shared SocketIO client for all three auction pages.
// Each page only wires up the buttons that exist in its own HTML.
(function () {
  const socket = io();

  const el = (id) => document.getElementById(id);

  function showError(message) {
    const box = el("bid-error");
    if (!box) return alert(message);
    box.textContent = message;
    box.style.display = "block";
    setTimeout(() => (box.style.display = "none"), 3000);
  }

  function renderState(state) {
    const noPlayer = el("no-player");
    const info = el("player-info");
    if (!info) return;

    if (state.active) {
      noPlayer.style.display = "none";
      info.style.display = "";
      el("p-name").textContent = state.player_name;
      el("p-role").textContent = state.player_role;
      el("p-base").textContent = state.base_price;
      el("p-bid").textContent = state.current_bid !== null ? state.current_bid + " L" : "—";
      el("p-team").textContent = state.leading_team || "No bids yet";
    } else {
      noPlayer.style.display = "";
      info.style.display = "none";
    }

    const ticker = el("ticker");
    if (ticker) {
      ticker.innerHTML = "";
      (state.history || []).forEach((line) => {
        const li = document.createElement("li");
        li.className = "list-group-item";
        li.textContent = line;
        ticker.appendChild(li);
      });
    }

    ["bid-button", "sold-button", "unsold-button"].forEach((id) => {
      const btn = el(id);
      if (btn) btn.disabled = !state.active;
    });
  }

  socket.on("state_update", renderState);
  socket.on("auction_error", (data) => showError(data.message));
  socket.on("player_done", () => {
    // Reload so purses, squads and feeds refresh from the database.
    setTimeout(() => window.location.reload(), 1200);
  });

  // Owner console
  const bidButton = el("bid-button");
  if (bidButton) {
    bidButton.addEventListener("click", () => socket.emit("place_bid", {}));
  }

  // Admin console
  const startButton = el("start-button");
  if (startButton) {
    startButton.addEventListener("click", () => {
      const unsoldSelect = el("unsold-select");
      const mainSelect = el("player-select");
      let playerId = null;
      if (unsoldSelect && unsoldSelect.value) playerId = unsoldSelect.value;
      else if (mainSelect && mainSelect.value) playerId = mainSelect.value;
      if (!playerId) return showError("Pick a player first.");
      socket.emit("start_player", { player_id: parseInt(playerId, 10) });
    });
  }
  const soldButton = el("sold-button");
  if (soldButton) {
    soldButton.addEventListener("click", () => socket.emit("mark_sold", {}));
  }
  const unsoldButton = el("unsold-button");
  if (unsoldButton) {
    unsoldButton.addEventListener("click", () => socket.emit("mark_unsold", {}));
  }
})();
