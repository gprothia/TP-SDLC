(function () {
  "use strict";

  const STAR_LABELS = {
    1: "1 of 5 — Needs improvement",
    2: "2 of 5 — Below expectations",
    3: "3 of 5 — Good",
    4: "4 of 5 — Great rescue",
    5: "5 of 5 — Outstanding!"
  };

  const ALL_TAGS = ["On time", "Friendly driver", "Explained the fix"];

  const INITIAL_DRIVERS = [
    {
      id: "marcus",
      name: "Marcus Rivera",
      truck: "Flatbed #418 · White Ford F-550",
      photo: "./images/marcus-rivera.jpg",
      baseStarsSum: 192,
      baseCount: 39,
      baseTags: { "On time": 31, "Friendly driver": 34, "Explained the fix": 24 },
      latestQuote: "Swapped my flat on I-95 in 12 minutes and checked the spare pressure too."
    },
    {
      id: "elena",
      name: "Elena Brooks",
      truck: "Service Van #204 · Blue Transit",
      photo: "./images/elena-brooks.jpg",
      baseStarsSum: 208,
      baseCount: 42,
      baseTags: { "On time": 36, "Friendly driver": 35, "Explained the fix": 33 },
      latestQuote: "Tested my alternator after the jump-start so I knew I could drive home safely."
    },
    {
      id: "maria",
      name: "Maria Santos",
      truck: "Flatbed #309 · White Ram 5500",
      photo: "./images/maria-santos.jpg",
      baseStarsSum: 186,
      baseCount: 38,
      baseTags: { "On time": 29, "Friendly driver": 33, "Explained the fix": 27 },
      latestQuote: "Calm, reassuring, and got our car loaded safely in the pouring rain."
    },
    {
      id: "sam",
      name: "Sam Patel",
      truck: "Utility Truck #112 · Silver F-350",
      photo: "./images/sam-patel.jpg",
      baseStarsSum: 165,
      baseCount: 34,
      baseTags: { "On time": 27, "Friendly driver": 26, "Explained the fix": 22 },
      latestQuote: "Unlocked my car in under five minutes without a scratch."
    },
    {
      id: "devon",
      name: "Devon Clark",
      truck: "Roadside Unit #507 · White F-450",
      photo: "./images/devon-clark.jpg",
      baseStarsSum: 147,
      baseCount: 31,
      baseTags: { "On time": 23, "Friendly driver": 25, "Explained the fix": 19 },
      latestQuote: "Brought fuel right to the exit ramp and followed me to the next station."
    }
  ];

  const INITIAL_RESCUES = [
    {
      id: "RSA-1042",
      helpType: "Flat tyre",
      location: "I-95 South, Mile 42",
      status: "completed",
      statusLabel: "Completed",
      timeLabel: "Completed today, 2:38 PM",
      driverId: "marcus",
      rating: null
    },
    {
      id: "RSA-1048",
      helpType: "Battery jump-start",
      location: "410 Oak Ave, Garage B",
      status: "en_route",
      statusLabel: "En route · 11 min",
      timeLabel: "ETA 11 min away",
      driverId: "elena",
      rating: null
    },
    {
      id: "RSA-1051",
      helpType: "Locked out",
      location: "Westgate Mall, Lot C",
      status: "en_route",
      statusLabel: "En route · 19 min",
      timeLabel: "ETA 19 min away",
      driverId: "sam",
      rating: null
    },
    {
      id: "RSA-1039",
      helpType: "Tow",
      location: "Route 9 & Elm St",
      status: "completed",
      statusLabel: "Completed",
      timeLabel: "Completed yesterday, 6:15 PM",
      driverId: "maria",
      rating: null
    },
    {
      id: "RSA-1031",
      helpType: "Out of fuel",
      location: "Highway 101, Exit 14",
      status: "completed",
      statusLabel: "Completed",
      timeLabel: "Completed Nov 18, 9:40 AM",
      driverId: "devon",
      rating: {
        stars: 5,
        tags: ["On time", "Friendly driver"],
        comment: "Arrived super fast and made sure the car started right up.",
        submittedAt: "Nov 18, 9:55 AM"
      }
    }
  ];

  function cloneState() {
    return {
      activeView: "rate", // "rate" | "thankyou" | "leaderboard"
      rescues: JSON.parse(JSON.stringify(INITIAL_RESCUES)),
      drivers: JSON.parse(JSON.stringify(INITIAL_DRIVERS)),
      selectedRescueId: "RSA-1042",
      rescueStatusFilter: "all",
      leaderboardTagFilter: "all",
      draftStars: 0,
      hoverStars: 0,
      draftTags: new Set(),
      draftComment: "",
      lastSubmittedRescueId: null,
      recentlyUpdatedDriverId: null
    };
  }

  let state = cloneState();

  // DOM References
  const navRateBtn = document.getElementById("navRateBtn");
  const navLeaderboardBtn = document.getElementById("navLeaderboardBtn");
  const brandHomeLink = document.getElementById("brandHomeLink");

  const rateView = document.getElementById("rateView");
  const thankYouView = document.getElementById("thankYouView");
  const leaderboardView = document.getElementById("leaderboardView");

  const rescueListEl = document.getElementById("rescueList");
  const rescueCountPill = document.getElementById("rescueCountPill");
  const statusFilterBtns = document.querySelectorAll("[data-status-filter]");

  const selectedDriverPhoto = document.getElementById("selectedDriverPhoto");
  const selectedRescueId = document.getElementById("selectedRescueId");
  const selectedStatusBadge = document.getElementById("selectedStatusBadge");
  const selectedDriverName = document.getElementById("selectedDriverName");
  const selectedRescueMeta = document.getElementById("selectedRescueMeta");
  const selectedRescueTime = document.getElementById("selectedRescueTime");
  const enrouteNotice = document.getElementById("enrouteNotice");
  const enrouteNoticeText = document.getElementById("enrouteNoticeText");
  const rateLead = document.getElementById("rateLead");

  const ratingForm = document.getElementById("ratingForm");
  const starBtns = document.querySelectorAll(".star-btn");
  const starCaption = document.getElementById("starCaption");
  const starError = document.getElementById("starError");
  const tagBtns = document.querySelectorAll(".tag-chip");
  const commentInput = document.getElementById("commentInput");
  const charCount = document.getElementById("charCount");
  const submitRatingBtn = document.getElementById("submitRatingBtn");
  const skipToLeaderboardBtn = document.getElementById("skipToLeaderboardBtn");

  // Thank-you elements
  const thankYouSub = document.getElementById("thankYouSub");
  const tyDriverPhoto = document.getElementById("tyDriverPhoto");
  const tyDriverName = document.getElementById("tyDriverName");
  const tyRescueMeta = document.getElementById("tyRescueMeta");
  const tyUpdatedAvg = document.getElementById("tyUpdatedAvg");
  const tyStars = document.getElementById("tyStars");
  const tyScoreText = document.getElementById("tyScoreText");
  const tyTags = document.getElementById("tyTags");
  const tyComment = document.getElementById("tyComment");
  const tyViewLeaderboardBtn = document.getElementById("tyViewLeaderboardBtn");
  const tyRateAnotherBtn = document.getElementById("tyRateAnotherBtn");
  const tyEditRatingBtn = document.getElementById("tyEditRatingBtn");

  // Leaderboard elements
  const copyPublicLinkBtn = document.getElementById("copyPublicLinkBtn");
  const metricAvgStars = document.getElementById("metricAvgStars");
  const metricTotalRatings = document.getElementById("metricTotalRatings");
  const metricDriverCount = document.getElementById("metricDriverCount");
  const lbTagFilterBtns = document.querySelectorAll("[data-lb-tag]");
  const lbBackToRateBtn = document.getElementById("lbBackToRateBtn");
  const podiumGrid = document.getElementById("podiumGrid");
  const standingsList = document.getElementById("standingsList");

  const resetDemoBtn = document.getElementById("resetDemoBtn");
  const toastEl = document.getElementById("toast");

  let toastTimer = null;
  function showToast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("show"), 3200);
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function starSvg(filled) {
    const color = filled ? "#F59E0B" : "#D2DCEB";
    return `<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="${color}" d="M12 2.4l2.92 5.92 6.53.95-4.72 4.6 1.11 6.5L12 17.3l-5.84 3.07 1.11-6.5-4.72-4.6 6.53-.95L12 2.4z"/></svg>`;
  }

  function renderInlineStars(avg) {
    const rounded = Math.round(avg);
    let html = "";
    for (let i = 1; i <= 5; i += 1) {
      html += starSvg(i <= rounded);
    }
    return html;
  }

  function getDriverById(driverId) {
    return state.drivers.find((d) => d.id === driverId);
  }

  function getRescueById(rescueId) {
    return state.rescues.find((r) => r.id === rescueId);
  }

  function computeDriverStats(driver) {
    let starsSum = driver.baseStarsSum;
    let count = driver.baseCount;
    const tagCounts = { ...driver.baseTags };
    let latestQuote = driver.latestQuote;

    // Incorporate any newly submitted / edited ratings from the prototype rescues list.
    // Note: RSA-1031 starts rated in INITIAL_RESCUES, so we compare against its initial state
    // to avoid double-counting on initial load while still reacting to edits.
    state.rescues.forEach((rescue) => {
      if (rescue.driverId !== driver.id) return;
      const initial = INITIAL_RESCUES.find((r) => r.id === rescue.id);
      const initiallyRated = Boolean(initial && initial.rating);

      if (rescue.rating && !initiallyRated) {
        starsSum += rescue.rating.stars;
        count += 1;
        rescue.rating.tags.forEach((t) => {
          tagCounts[t] = (tagCounts[t] || 0) + 1;
        });
        if (rescue.rating.comment) {
          latestQuote = rescue.rating.comment;
        }
      } else if (rescue.rating && initiallyRated) {
        // Adjust delta if the pre-rated rescue was edited
        const deltaStars = rescue.rating.stars - initial.rating.stars;
        starsSum += deltaStars;
        ALL_TAGS.forEach((t) => {
          const had = initial.rating.tags.includes(t) ? 1 : 0;
          const has = rescue.rating.tags.includes(t) ? 1 : 0;
          tagCounts[t] = Math.max(0, (tagCounts[t] || 0) + (has - had));
        });
        if (rescue.rating.comment && rescue.rating.comment !== initial.rating.comment) {
          latestQuote = rescue.rating.comment;
        }
      }
    });

    const avg = count > 0 ? starsSum / count : 0;
    return {
      ...driver,
      avg,
      avgFormatted: avg.toFixed(2),
      count,
      tagCounts,
      latestQuote
    };
  }

  function getRankedDrivers() {
    const computed = state.drivers.map(computeDriverStats);
    computed.sort((a, b) => {
      if (state.leaderboardTagFilter !== "all") {
        const tag = state.leaderboardTagFilter;
        const diffTag = (b.tagCounts[tag] || 0) - (a.tagCounts[tag] || 0);
        if (diffTag !== 0) return diffTag;
      }
      if (Math.abs(b.avg - a.avg) > 0.0001) return b.avg - a.avg;
      return b.count - a.count;
    });
    return computed;
  }

  function loadDraftFromSelectedRescue() {
    const rescue = getRescueById(state.selectedRescueId);
    if (!rescue) return;
    if (rescue.rating) {
      state.draftStars = rescue.rating.stars;
      state.draftTags = new Set(rescue.rating.tags);
      state.draftComment = rescue.rating.comment || "";
    } else {
      state.draftStars = 0;
      state.draftTags = new Set();
      state.draftComment = "";
    }
    state.hoverStars = 0;
    starError.hidden = true;
  }

  function setView(viewName) {
    state.activeView = viewName;
    rateView.hidden = viewName !== "rate";
    thankYouView.hidden = viewName !== "thankyou";
    leaderboardView.hidden = viewName !== "leaderboard";

    navRateBtn.classList.toggle("active", viewName === "rate" || viewName === "thankyou");
    navLeaderboardBtn.classList.toggle("active", viewName === "leaderboard");

    if (viewName === "rate") {
      renderRescueList();
      renderRatingCard();
    } else if (viewName === "thankyou") {
      renderThankYou();
    } else if (viewName === "leaderboard") {
      renderLeaderboard();
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function renderRescueList() {
    const filtered = state.rescues.filter((r) => {
      if (state.rescueStatusFilter === "all") return true;
      return r.status === state.rescueStatusFilter;
    });

    rescueCountPill.textContent = String(filtered.length);

    statusFilterBtns.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.statusFilter === state.rescueStatusFilter);
    });

    rescueListEl.innerHTML = filtered
      .map((rescue) => {
        const driver = getDriverById(rescue.driverId);
        const isSelected = rescue.id === state.selectedRescueId;
        const badgeClass = rescue.status === "completed" ? "completed" : "en_route";
        const ratingHtml = rescue.rating
          ? `<span class="rated-mini">★ ${rescue.rating.stars}.0</span>`
          : `<span class="unrated-mini">Rate &rarr;</span>`;

        return `
          <li>
            <button
              type="button"
              class="rescue-item-btn ${isSelected ? "selected" : ""}"
              data-rescue-id="${rescue.id}"
              aria-current="${isSelected ? "true" : "false"}"
            >
              <img class="driver-photo-sm" src="${driver.photo}" alt="${escapeHtml(driver.name)}" width="42" height="42" />
              <div class="rescue-item-body">
                <div class="rescue-item-top">
                  <span class="rescue-item-title">${escapeHtml(rescue.helpType)}</span>
                  <span class="rescue-id">#${rescue.id}</span>
                </div>
                <div class="rescue-item-sub">${escapeHtml(driver.name)} &bull; ${escapeHtml(rescue.location)}</div>
                <div class="rescue-item-bottom">
                  <span class="status-badge ${badgeClass}">
                    <span class="status-dot"></span>
                    ${escapeHtml(rescue.statusLabel)}
                  </span>
                  ${ratingHtml}
                </div>
              </div>
            </button>
          </li>
        `;
      })
      .join("");

    rescueListEl.querySelectorAll("[data-rescue-id]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.selectedRescueId = btn.dataset.rescueId;
        loadDraftFromSelectedRescue();
        renderRescueList();
        renderRatingCard();
      });
    });
  }

  function renderStarsUI() {
    const activeVal = state.hoverStars || state.draftStars;
    starBtns.forEach((btn) => {
      const val = Number(btn.dataset.star);
      const isSelected = val <= state.draftStars;
      const isPreview = state.hoverStars > 0 && val <= state.hoverStars && !isSelected;
      btn.classList.toggle("filled", isSelected || (state.hoverStars > 0 && val <= state.hoverStars));
      btn.classList.toggle("preview", isPreview);
      btn.setAttribute("aria-checked", String(val === state.draftStars));
    });

    if (activeVal > 0) {
      starCaption.textContent = STAR_LABELS[activeVal];
      starCaption.classList.add("has-value");
    } else {
      starCaption.textContent = "Select a star rating (1 to 5)";
      starCaption.classList.remove("has-value");
    }
  }

  function renderTagsUI() {
    tagBtns.forEach((btn) => {
      const pressed = state.draftTags.has(btn.dataset.tag);
      btn.setAttribute("aria-pressed", String(pressed));
    });
  }

  function renderRatingCard() {
    const rescue = getRescueById(state.selectedRescueId);
    if (!rescue) return;
    const driver = getDriverById(rescue.driverId);

    selectedDriverPhoto.src = driver.photo;
    selectedDriverPhoto.alt = driver.name;
    selectedRescueId.textContent = `#${rescue.id}`;
    selectedStatusBadge.textContent = rescue.statusLabel;
    selectedStatusBadge.className = `status-badge ${rescue.status === "completed" ? "completed" : "en_route"}`;
    selectedDriverName.textContent = driver.name;
    selectedRescueMeta.textContent = `${rescue.helpType} • ${rescue.location} • ${driver.truck.split(" · ")[0]}`;
    selectedRescueTime.textContent = rescue.timeLabel;

    if (rescue.status === "en_route") {
      enrouteNotice.hidden = false;
      enrouteNoticeText.textContent = `${driver.name} is still en route (${rescue.timeLabel}). You can still submit a rating right now.`;
      rateLead.textContent = `Share early feedback for ${driver.name} while they are on the way.`;
    } else {
      enrouteNotice.hidden = true;
      rateLead.textContent = `Share a quick rating for ${driver.name} so we can recognize great rescues.`;
    }

    submitRatingBtn.textContent = rescue.rating ? "Update rating" : "Submit rating";
    commentInput.value = state.draftComment;
    charCount.textContent = `${state.draftComment.length} / 300`;

    renderStarsUI();
    renderTagsUI();
  }

  function renderThankYou() {
    const rescue = getRescueById(state.lastSubmittedRescueId || state.selectedRescueId);
    if (!rescue || !rescue.rating) return;
    const driver = getDriverById(rescue.driverId);
    const stats = computeDriverStats(driver);

    const statusNote =
      rescue.status === "en_route"
        ? `Your early rating for ${driver.name} (#${rescue.id}, currently en route) has been recorded.`
        : `Your rating for ${driver.name} (#${rescue.id}) helps us celebrate great roadside rescues.`;
    thankYouSub.textContent = statusNote;

    tyDriverPhoto.src = driver.photo;
    tyDriverPhoto.alt = driver.name;
    tyDriverName.textContent = driver.name;
    tyRescueMeta.textContent = `#${rescue.id} • ${rescue.helpType} • ${rescue.statusLabel}`;
    tyUpdatedAvg.textContent = `★ ${stats.avgFormatted} avg (${stats.count})`;

    tyStars.innerHTML = renderInlineStars(rescue.rating.stars);
    tyScoreText.textContent = `${rescue.rating.stars} out of 5 stars`;

    if (rescue.rating.tags.length > 0) {
      tyTags.innerHTML = rescue.rating.tags
        .map((tag) => `<span class="receipt-tag">${escapeHtml(tag)}</span>`)
        .join("");
    } else {
      tyTags.innerHTML = `<span class="receipt-tag-muted">No highlight tags selected</span>`;
    }

    if (rescue.rating.comment) {
      tyComment.hidden = false;
      tyComment.textContent = `“${rescue.rating.comment}”`;
    } else {
      tyComment.hidden = true;
    }
  }

  function renderLeaderboard() {
    const ranked = getRankedDrivers();

    const totalRatings = ranked.reduce((sum, d) => sum + d.count, 0);
    const weightedStars = ranked.reduce((sum, d) => sum + d.avg * d.count, 0);
    const fleetAvg = totalRatings > 0 ? (weightedStars / totalRatings).toFixed(2) : "0.00";

    metricAvgStars.textContent = fleetAvg;
    metricTotalRatings.textContent = String(totalRatings);
    metricDriverCount.textContent = String(ranked.length);

    lbTagFilterBtns.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lbTag === state.leaderboardTagFilter);
    });

    // Top 3 Podium
    const topThree = ranked.slice(0, 3);
    podiumGrid.innerHTML = topThree
      .map((driver, idx) => {
        const rank = idx + 1;
        const isUpdated = driver.id === state.recentlyUpdatedDriverId;
        const topTags = ALL_TAGS.slice()
          .sort((a, b) => (driver.tagCounts[b] || 0) - (driver.tagCounts[a] || 0))
          .slice(0, 2);

        return `
          <article class="podium-card rank-${rank}">
            <span class="rank-badge rank-${rank}">#${rank}</span>
            ${isUpdated ? `<span class="updated-pill">Just updated</span>` : ""}
            <img class="podium-photo" src="${driver.photo}" alt="${escapeHtml(driver.name)}" width="84" height="84" />
            <h3 class="podium-name">${escapeHtml(driver.name)}</h3>
            <p class="podium-truck">${escapeHtml(driver.truck)}</p>
            <div class="podium-stars-block">
              <span class="avg-number">${driver.avgFormatted}</span>
              <span class="inline-stars" aria-label="${driver.avgFormatted} out of 5 stars">${renderInlineStars(driver.avg)}</span>
            </div>
            <div class="podium-count">${driver.count} ratings this month</div>
            <div class="podium-tags">
              ${topTags
                .map((tag) => `<span class="mini-tag">${escapeHtml(tag)} (${driver.tagCounts[tag] || 0})</span>`)
                .join("")}
            </div>
          </article>
        `;
      })
      .join("");

    // Full Standings List
    standingsList.innerHTML = ranked
      .map((driver, idx) => {
        const rank = idx + 1;
        const isUpdated = driver.id === state.recentlyUpdatedDriverId;
        const tagsHtml = ALL_TAGS.map((tag) => {
          const isFiltered = state.leaderboardTagFilter === tag;
          const style = isFiltered ? ' style="background:#0B3D91;color:#FFFFFF;"' : "";
          return `<span class="mini-tag"${style}>${escapeHtml(tag)} &middot; ${driver.tagCounts[tag] || 0}</span>`;
        }).join("");

        return `
          <li class="standing-row ${isUpdated ? "highlighted" : ""}">
            <div class="standing-rank">#${rank}</div>
            <img class="standing-photo" src="${driver.photo}" alt="${escapeHtml(driver.name)}" width="48" height="48" />
            <div class="standing-main">
              <div class="standing-name-line">
                <span class="standing-name">${escapeHtml(driver.name)}</span>
                <span class="standing-truck">${escapeHtml(driver.truck)}</span>
                ${isUpdated ? `<span class="status-badge completed">Updated with your rating</span>` : ""}
              </div>
              <p class="standing-quote">“${escapeHtml(driver.latestQuote)}”</p>
              <div class="standing-tags">${tagsHtml}</div>
            </div>
            <div class="standing-score-col">
              <div class="standing-avg-row">
                <span class="inline-stars" aria-hidden="true">${starSvg(true)}</span>
                <span class="standing-avg">${driver.avgFormatted}</span>
              </div>
              <span class="standing-reviews">${driver.count} ratings</span>
            </div>
          </li>
        `;
      })
      .join("");
  }

  // Event Listeners — Navigation
  navRateBtn.addEventListener("click", () => setView("rate"));
  navLeaderboardBtn.addEventListener("click", () => setView("leaderboard"));
  brandHomeLink.addEventListener("click", (e) => {
    e.preventDefault();
    setView("rate");
  });
  skipToLeaderboardBtn.addEventListener("click", () => setView("leaderboard"));
  lbBackToRateBtn.addEventListener("click", () => setView("rate"));

  // Rescue status filters
  statusFilterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      state.rescueStatusFilter = btn.dataset.statusFilter;
      const visible = state.rescues.filter(
        (r) => state.rescueStatusFilter === "all" || r.status === state.rescueStatusFilter
      );
      if (visible.length > 0 && !visible.some((r) => r.id === state.selectedRescueId)) {
        state.selectedRescueId = visible[0].id;
        loadDraftFromSelectedRescue();
        renderRatingCard();
      }
      renderRescueList();
    });
  });

  // 5-Star Interactions
  starBtns.forEach((btn) => {
    const starVal = Number(btn.dataset.star);
    btn.addEventListener("mouseenter", () => {
      state.hoverStars = starVal;
      renderStarsUI();
    });
    btn.addEventListener("mouseleave", () => {
      state.hoverStars = 0;
      renderStarsUI();
    });
    btn.addEventListener("click", () => {
      state.draftStars = starVal;
      state.hoverStars = 0;
      starError.hidden = true;
      renderStarsUI();
    });
    btn.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowUp") {
        e.preventDefault();
        state.draftStars = Math.min(5, (state.draftStars || 0) + 1);
        starError.hidden = true;
        renderStarsUI();
      } else if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
        e.preventDefault();
        state.draftStars = Math.max(1, (state.draftStars || 2) - 1);
        starError.hidden = true;
        renderStarsUI();
      }
    });
  });

  // Tag toggles
  tagBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tag = btn.dataset.tag;
      if (state.draftTags.has(tag)) {
        state.draftTags.delete(tag);
      } else {
        state.draftTags.add(tag);
      }
      renderTagsUI();
    });
  });

  // Comment input
  commentInput.addEventListener("input", () => {
    state.draftComment = commentInput.value;
    charCount.textContent = `${state.draftComment.length} / 300`;
  });

  // Submit rating
  ratingForm.addEventListener("submit", (e) => {
    e.preventDefault();
    if (state.draftStars < 1 || state.draftStars > 5) {
      starError.hidden = false;
      return;
    }

    const rescue = getRescueById(state.selectedRescueId);
    if (!rescue) return;

    rescue.rating = {
      stars: state.draftStars,
      tags: Array.from(state.draftTags),
      comment: state.draftComment.trim(),
      submittedAt: "Just now"
    };

    state.lastSubmittedRescueId = rescue.id;
    state.recentlyUpdatedDriverId = rescue.driverId;
    setView("thankyou");
  });

  // Thank-you screen actions
  tyViewLeaderboardBtn.addEventListener("click", () => setView("leaderboard"));

  tyRateAnotherBtn.addEventListener("click", () => {
    const nextUnrated = state.rescues.find((r) => !r.rating);
    if (nextUnrated) {
      state.selectedRescueId = nextUnrated.id;
      state.rescueStatusFilter = "all";
    }
    loadDraftFromSelectedRescue();
    setView("rate");
  });

  tyEditRatingBtn.addEventListener("click", () => {
    if (state.lastSubmittedRescueId) {
      state.selectedRescueId = state.lastSubmittedRescueId;
    }
    loadDraftFromSelectedRescue();
    setView("rate");
  });

  // Leaderboard tag filters & copy public link
  lbTagFilterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      state.leaderboardTagFilter = btn.dataset.lbTag;
      renderLeaderboard();
    });
  });

  copyPublicLinkBtn.addEventListener("click", () => {
    const fakePublicUrl = "https://aaa-demo.example/top-drivers";
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(fakePublicUrl).catch(() => {});
    }
    showToast("Public leaderboard link copied! Anyone can view it without signing in.");
  });

  // Reset demo
  resetDemoBtn.addEventListener("click", () => {
    state = cloneState();
    loadDraftFromSelectedRescue();
    setView("rate");
    showToast("Demo data reset.");
  });

  // Initialize
  loadDraftFromSelectedRescue();
  renderRescueList();
  renderRatingCard();
})();
