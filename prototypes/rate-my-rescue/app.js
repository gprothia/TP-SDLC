(function () {
  "use strict";

  const STAR_LABELS = {
    0: "Tap a star to rate",
    1: "1 star — Needs improvement",
    2: "2 stars — Below expectations",
    3: "3 stars — Okay",
    4: "4 stars — Good service",
    5: "5 stars — Outstanding!"
  };

  function createInitialState() {
    return {
      drivers: {
        sam: {
          id: "sam",
          name: "Sam Rivera",
          photo: "avatars/sam.svg",
          unit: "Truck #T-204 · North Metro",
          topTag: "Friendly driver",
          rescuesThisMonth: 47,
          totalStars: 230, // 4.89 -> 4.9
          ratingCount: 47
        },
        maria: {
          id: "maria",
          name: "Maria Chen",
          photo: "avatars/maria.svg",
          unit: "Truck #T-118 · Harbor District",
          topTag: "On time",
          rescuesThisMonth: 52,
          totalStars: 250, // 4.81 -> 4.8
          ratingCount: 52
        },
        elena: {
          id: "elena",
          name: "Elena Ortiz",
          photo: "avatars/elena.svg",
          unit: "Truck #T-309 · Pinecrest",
          topTag: "Explained the fix",
          rescuesThisMonth: 39,
          totalStars: 186, // 4.77 -> 4.8
          ratingCount: 39
        },
        marcus: {
          id: "marcus",
          name: "Marcus Vance",
          photo: "avatars/marcus.svg",
          unit: "Truck #T-412 · I-95 Corridor",
          topTag: "On time",
          rescuesThisMonth: 34,
          totalStars: 160, // 4.71 -> 4.7
          ratingCount: 34
        },
        devon: {
          id: "devon",
          name: "Devon Brooks",
          photo: "avatars/devon.svg",
          unit: "Truck #T-155 · Westside",
          topTag: "Friendly driver",
          rescuesThisMonth: 28,
          totalStars: 129, // 4.61 -> 4.6
          ratingCount: 28
        }
      },
      rescues: [
        {
          id: "RSA-1042",
          helpType: "Battery jump-start",
          location: "1420 Oakridge Ave",
          when: "Today, 2:15 PM",
          status: "completed",
          eta: null,
          driverId: "sam",
          rating: null
        },
        {
          id: "RSA-1049",
          helpType: "Tow",
          location: "I-95 Milepost 44",
          when: "Active now",
          status: "en_route",
          eta: "ETA 11 min",
          driverId: "marcus",
          rating: null
        },
        {
          id: "RSA-1051",
          helpType: "Locked out",
          location: "Pinecrest Mall Lot B",
          when: "Active now",
          status: "en_route",
          eta: "ETA 18 min",
          driverId: "elena",
          rating: null
        },
        {
          id: "RSA-1038",
          helpType: "Flat tyre",
          location: "88 Harbor Blvd",
          when: "3 days ago",
          status: "completed",
          eta: null,
          driverId: "maria",
          rating: null
        },
        {
          id: "RSA-1024",
          helpType: "Out of fuel",
          location: "Hwy 101 Exit 19",
          when: "2 weeks ago",
          status: "completed",
          eta: null,
          driverId: "devon",
          rating: {
            stars: 5,
            tags: ["On time", "Explained the fix"],
            comment: "Quick delivery and checked the fuel gauge before leaving."
          }
        }
      ],
      activeView: "rate",
      selectedRescueId: "RSA-1042",
      listFilter: "all",
      formStars: 0,
      formTags: new Set(),
      lastSubmittedRescueId: null
    };
  }

  let state = createInitialState();

  // DOM references
  const views = {
    rate: document.getElementById("view-rate"),
    list: document.getElementById("view-list"),
    thanks: document.getElementById("view-thanks"),
    leaderboard: document.getElementById("view-leaderboard")
  };
  const navTabs = document.querySelectorAll(".nav-tab");
  const starButtons = document.querySelectorAll(".star-btn");
  const starCaption = document.getElementById("star-caption");
  const starError = document.getElementById("star-error");
  const tagButtons = document.querySelectorAll(".tag-pill");
  const commentInput = document.getElementById("rating-comment");
  const charCount = document.getElementById("char-count");
  const ratingForm = document.getElementById("rating-form");
  const rescueListEl = document.getElementById("rescue-list");
  const filterButtons = document.querySelectorAll(".filter-pill");
  const leaderboardListEl = document.getElementById("leaderboard-list");

  function getRescue(id) {
    return state.rescues.find((r) => r.id === id) || state.rescues[0];
  }

  function showView(viewName) {
    state.activeView = viewName;
    Object.entries(views).forEach(([key, el]) => {
      el.classList.toggle("active", key === viewName);
    });

    navTabs.forEach((tab) => {
      const target = tab.dataset.view;
      const isCurrent = target === viewName || (viewName === "thanks" && target === "rate");
      tab.classList.toggle("active", isCurrent);
    });

    if (viewName === "rate") renderRateScreen();
    if (viewName === "list") renderRescueList();
    if (viewName === "thanks") renderThanksScreen();
    if (viewName === "leaderboard") renderLeaderboard();

    window.scrollTo({ top: 0, behavior: "instant" });
  }

  function openRescueForRating(rescueId) {
    state.selectedRescueId = rescueId;
    const rescue = getRescue(rescueId);
    if (rescue.rating) {
      state.formStars = rescue.rating.stars;
      state.formTags = new Set(rescue.rating.tags);
      commentInput.value = rescue.rating.comment;
    } else {
      state.formStars = 0;
      state.formTags = new Set();
      commentInput.value = "";
    }
    starError.classList.add("hidden");
    updateCharCount();
    showView("rate");
  }

  function renderRateScreen() {
    const rescue = getRescue(state.selectedRescueId);
    const driver = state.drivers[rescue.driverId];

    document.getElementById("rate-rescue-id").textContent = rescue.id;
    const badge = document.getElementById("rate-status-badge");
    badge.className = "status-badge " + rescue.status;
    badge.textContent = rescue.status === "en_route" ? "En route" : "Completed";

    const photo = document.getElementById("rate-driver-photo");
    photo.src = driver.photo;
    photo.alt = "Driver " + driver.name;
    document.getElementById("rate-driver-name").textContent = driver.name;

    const summaryParts = [rescue.helpType, rescue.location, rescue.when];
    document.getElementById("rate-rescue-summary").textContent = summaryParts.join(" · ");

    const notice = document.getElementById("enroute-notice");
    if (rescue.status === "en_route") {
      document.getElementById("enroute-eta").textContent = rescue.eta || "on the way";
      notice.classList.remove("hidden");
    } else {
      notice.classList.add("hidden");
    }

    const submitBtn = document.getElementById("btn-submit-rating");
    submitBtn.textContent = rescue.rating ? "Update rating" : "Submit rating";

    renderStars(state.formStars, 0);
    renderTags();
    updateCharCount();
  }

  function renderStars(selected, hoverVal) {
    const activeCutoff = hoverVal || selected;
    starButtons.forEach((btn) => {
      const value = Number(btn.dataset.star);
      btn.classList.toggle("selected", value <= selected);
      btn.classList.toggle("preview", hoverVal > 0 && value <= hoverVal);
      btn.setAttribute("aria-checked", value === selected ? "true" : "false");
    });
    starCaption.textContent = STAR_LABELS[activeCutoff] || STAR_LABELS[0];
  }

  function renderTags() {
    tagButtons.forEach((btn) => {
      const isSelected = state.formTags.has(btn.dataset.tag);
      btn.classList.toggle("active", isSelected);
      btn.setAttribute("aria-pressed", isSelected ? "true" : "false");
    });
  }

  function updateCharCount() {
    charCount.textContent = `${commentInput.value.length} / 300`;
  }

  function renderRescueList() {
    document.getElementById("rescue-count").textContent = String(state.rescues.length);
    rescueListEl.innerHTML = "";

    const filtered = state.rescues.filter((r) => {
      if (state.listFilter === "all") return true;
      return r.status === state.listFilter;
    });

    filtered.forEach((rescue) => {
      const driver = state.drivers[rescue.driverId];
      const card = document.createElement("article");
      card.className = "card rescue-item";

      const left = document.createElement("div");
      left.className = "rescue-item-left";

      const img = document.createElement("img");
      img.className = "driver-avatar small";
      img.src = driver.photo;
      img.alt = "Driver " + driver.name;

      const body = document.createElement("div");

      const head = document.createElement("div");
      head.className = "rescue-item-head";

      const idEl = document.createElement("span");
      idEl.className = "rescue-id";
      idEl.textContent = rescue.id;

      const statusEl = document.createElement("span");
      statusEl.className = "status-badge " + rescue.status;
      statusEl.textContent = rescue.status === "en_route"
        ? `En route · ${rescue.eta}`
        : "Completed";

      head.append(idEl, statusEl);

      const titleEl = document.createElement("div");
      titleEl.className = "rescue-item-title";
      titleEl.textContent = `${rescue.helpType} · Driver: ${driver.name}`;

      const subEl = document.createElement("div");
      subEl.className = "rescue-item-sub";
      subEl.textContent = `${rescue.location} · ${rescue.when}`;

      body.append(head, titleEl, subEl);

      if (rescue.rating) {
        const ratedEl = document.createElement("div");
        ratedEl.className = "rescue-item-rated";
        ratedEl.textContent = `Rated ${"★".repeat(rescue.rating.stars)} (${rescue.rating.stars}/5)`;
        body.appendChild(ratedEl);
      }

      left.append(img, body);

      const actionWrap = document.createElement("div");
      actionWrap.className = "rescue-item-action";

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = rescue.rating ? "btn-secondary" : "btn-primary";
      btn.textContent = rescue.rating ? "Edit rating" : "Rate rescue";
      btn.addEventListener("click", () => openRescueForRating(rescue.id));

      actionWrap.appendChild(btn);
      card.append(left, actionWrap);
      rescueListEl.appendChild(card);
    });
  }

  function submitCurrentRating(event) {
    event.preventDefault();
    if (state.formStars < 1 || state.formStars > 5) {
      starError.classList.remove("hidden");
      return;
    }
    starError.classList.add("hidden");

    const rescue = getRescue(state.selectedRescueId);
    const driver = state.drivers[rescue.driverId];
    const previousRating = rescue.rating;
    const newComment = commentInput.value.trim();
    const newTags = Array.from(state.formTags);

    if (previousRating) {
      driver.totalStars = driver.totalStars - previousRating.stars + state.formStars;
    } else {
      driver.totalStars += state.formStars;
      driver.ratingCount += 1;
    }

    if (newTags.length > 0) {
      driver.topTag = newTags[0];
    }

    rescue.rating = {
      stars: state.formStars,
      tags: newTags,
      comment: newComment
    };

    state.lastSubmittedRescueId = rescue.id;
    showView("thanks");
  }

  function renderThanksScreen() {
    const rescue = getRescue(state.lastSubmittedRescueId || state.selectedRescueId);
    const driver = state.drivers[rescue.driverId];
    const rating = rescue.rating;

    document.getElementById("thanks-subtitle").textContent =
      `Your rating for ${driver.name} on rescue ${rescue.id} has been recorded.`;

    const photo = document.getElementById("thanks-driver-photo");
    photo.src = driver.photo;
    photo.alt = "Driver " + driver.name;

    document.getElementById("thanks-driver-name").textContent = driver.name;
    document.getElementById("thanks-rescue-meta").textContent =
      `${rescue.id} · ${rescue.helpType} · ${rescue.status === "en_route" ? "En route" : "Completed"}`;

    const starsEl = document.getElementById("thanks-stars");
    starsEl.textContent = "★".repeat(rating.stars) + "☆".repeat(5 - rating.stars);

    const tagsEl = document.getElementById("thanks-tags");
    tagsEl.innerHTML = "";
    if (rating.tags.length > 0) {
      rating.tags.forEach((tag) => {
        const chip = document.createElement("span");
        chip.className = "summary-tag";
        chip.textContent = tag;
        tagsEl.appendChild(chip);
      });
      tagsEl.classList.remove("hidden");
    } else {
      tagsEl.classList.add("hidden");
    }

    const commentEl = document.getElementById("thanks-comment");
    if (rating.comment) {
      commentEl.textContent = `"${rating.comment}"`;
      commentEl.classList.remove("hidden");
    } else {
      commentEl.classList.add("hidden");
    }

    const avg = (driver.totalStars / driver.ratingCount).toFixed(1);
    document.getElementById("thanks-leaderboard-hint").textContent =
      `${driver.name}'s monthly average is now ${avg} ★ (${driver.ratingCount} ratings).`;
  }

  function renderLeaderboard() {
    leaderboardListEl.innerHTML = "";
    const sorted = Object.values(state.drivers).sort((a, b) => {
      const avgDiff = b.totalStars / b.ratingCount - a.totalStars / a.ratingCount;
      if (Math.abs(avgDiff) > 0.001) return avgDiff;
      return b.ratingCount - a.ratingCount;
    });

    sorted.forEach((driver, index) => {
      const rank = index + 1;
      const avg = (driver.totalStars / driver.ratingCount).toFixed(1);

      const card = document.createElement("article");
      card.className = "card leader-card" + (rank === 1 ? " top-1" : "");

      const rankEl = document.createElement("div");
      rankEl.className = "leader-rank" + (rank <= 3 ? ` rank-${rank}` : "");
      rankEl.textContent = `#${rank}`;

      const img = document.createElement("img");
      img.className = "driver-avatar";
      img.src = driver.photo;
      img.alt = "Driver " + driver.name;

      const info = document.createElement("div");
      info.className = "leader-info";

      const nameRow = document.createElement("div");
      nameRow.className = "leader-name-row";

      const nameEl = document.createElement("span");
      nameEl.className = "leader-name";
      nameEl.textContent = driver.name;

      const tagEl = document.createElement("span");
      tagEl.className = "leader-tag";
      tagEl.textContent = driver.topTag;

      nameRow.append(nameEl, tagEl);

      const metaEl = document.createElement("div");
      metaEl.className = "leader-meta";
      metaEl.textContent = `${driver.unit} · ${driver.rescuesThisMonth} rescues this month`;

      info.append(nameRow, metaEl);

      const score = document.createElement("div");
      score.className = "leader-score";

      const avgEl = document.createElement("div");
      avgEl.className = "leader-avg";
      avgEl.innerHTML = `<span class="leader-star-icon" aria-hidden="true">★</span>`;
      const avgText = document.createElement("span");
      avgText.textContent = avg;
      avgEl.appendChild(avgText);

      const countEl = document.createElement("div");
      countEl.className = "leader-count";
      countEl.textContent = `${driver.ratingCount} ratings`;

      score.append(avgEl, countEl);
      card.append(rankEl, img, info, score);
      leaderboardListEl.appendChild(card);
    });
  }

  // Event listeners
  navTabs.forEach((tab) => {
    tab.addEventListener("click", () => showView(tab.dataset.view));
  });

  document.getElementById("btn-switch-rescue").addEventListener("click", () => showView("list"));
  document.getElementById("btn-go-leaderboard").addEventListener("click", () => showView("leaderboard"));
  document.getElementById("btn-rate-another").addEventListener("click", () => showView("list"));
  document.getElementById("btn-leaderboard-rate").addEventListener("click", () => showView("list"));

  starButtons.forEach((btn) => {
    const val = Number(btn.dataset.star);
    btn.addEventListener("click", () => {
      state.formStars = val;
      starError.classList.add("hidden");
      renderStars(state.formStars, 0);
    });
    btn.addEventListener("mouseenter", () => renderStars(state.formStars, val));
    btn.addEventListener("mouseleave", () => renderStars(state.formStars, 0));
  });

  tagButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tag = btn.dataset.tag;
      if (state.formTags.has(tag)) {
        state.formTags.delete(tag);
      } else {
        state.formTags.add(tag);
      }
      renderTags();
    });
  });

  commentInput.addEventListener("input", updateCharCount);
  ratingForm.addEventListener("submit", submitCurrentRating);

  filterButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      state.listFilter = btn.dataset.filter;
      filterButtons.forEach((b) => b.classList.toggle("active", b === btn));
      renderRescueList();
    });
  });

  document.getElementById("btn-reset-demo").addEventListener("click", () => {
    state = createInitialState();
    commentInput.value = "";
    filterButtons.forEach((b) => b.classList.toggle("active", b.dataset.filter === "all"));
    showView("rate");
  });

  // Initial render
  renderRateScreen();
})();
