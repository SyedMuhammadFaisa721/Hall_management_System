
/* =========================================================
   HALLMASTER — BASE JAVASCRIPT
========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    /* =====================================================
       ELEMENTS
    ===================================================== */

    const sidebar = document.getElementById("sidebar");
    const sidebarOverlay = document.getElementById("sidebarOverlay");
    const sidebarClose = document.getElementById("sidebarClose");
    const menuToggle = document.getElementById("menuToggle");

    const notificationButton =
        document.getElementById("notificationButton");

    const notificationPanel =
        document.getElementById("notificationPanel");

    const markNotificationsRead =
        document.getElementById("markNotificationsRead");

    const userProfileButton =
        document.getElementById("userProfileButton");

    const userDropdown =
        document.getElementById("userDropdown");

    const quickActionButton =
        document.getElementById("quickActionButton");

    const logoutButton =
        document.getElementById("logoutButton");

    const globalSearch =
        document.getElementById("globalSearch");

    const globalSearchInput =
        document.getElementById("globalSearchInput");

    const searchResultsOverlay =
        document.getElementById("searchResultsOverlay");

    const closeSearchResultsButton =
        document.getElementById("closeSearchResults");

    const searchResultTitle =
        document.getElementById("searchResultTitle");

    const searchResultsContent =
        document.getElementById("searchResultsContent");

    const globalModal =
        document.getElementById("globalModal");

    const modalClose =
        document.getElementById("modalClose");

    const modalContent =
        document.getElementById("modalContent");

    const toastContainer =
        document.getElementById("toastContainer");

    const currentDate =
        document.getElementById("currentDate");

    const greeting =
        document.getElementById("greeting");


    /* =====================================================
       MOBILE SIDEBAR
    ===================================================== */

    function openSidebar() {

        if (!sidebar) return;

        sidebar.classList.add("open");

        if (sidebarOverlay) {
            sidebarOverlay.classList.add("show");
        }

        if (menuToggle) {
            menuToggle.setAttribute(
                "aria-expanded",
                "true"
            );
        }

        document.body.style.overflow = "hidden";
    }


    function closeSidebarMenu() {

        if (!sidebar) return;

        sidebar.classList.remove("open");

        if (sidebarOverlay) {
            sidebarOverlay.classList.remove("show");
        }

        if (menuToggle) {
            menuToggle.setAttribute(
                "aria-expanded",
                "false"
            );
        }

        document.body.style.overflow = "";
    }


    if (menuToggle) {

        menuToggle.addEventListener(
            "click",
            openSidebar
        );
    }


    if (sidebarClose) {

        sidebarClose.addEventListener(
            "click",
            closeSidebarMenu
        );
    }


    if (sidebarOverlay) {

        sidebarOverlay.addEventListener(
            "click",
            closeSidebarMenu
        );
    }


    /* =====================================================
       CLOSE SIDEBAR AFTER NAVIGATION — MOBILE
    ===================================================== */

    const navItems =
        document.querySelectorAll(".nav-item");

    navItems.forEach(item => {

        item.addEventListener("click", () => {

            if (window.innerWidth <= 800) {
                closeSidebarMenu();
            }

        });

    });


    /* =====================================================
       ACTIVE NAVIGATION
    ===================================================== */

    const currentPage =
        window.location.pathname
            .split("/")
            .pop()
            .toLowerCase();


    navItems.forEach(item => {

        const href =
            item.getAttribute("href");

        if (!href) return;

        const pageName =
            href.split("/").pop().toLowerCase();

        item.classList.remove("active");

        if (
            pageName === currentPage ||
            (
                currentPage === "" &&
                pageName === "index.html"
            )
        ) {
            item.classList.add("active");
        }

    });


    /* =====================================================
       NOTIFICATION DROPDOWN
    ===================================================== */

    function closeNotificationPanel() {

        if (!notificationPanel) return;

        notificationPanel.classList.remove("show");

        if (notificationButton) {
            notificationButton.setAttribute(
                "aria-expanded",
                "false"
            );
        }
    }


    function openNotificationPanel() {

        if (!notificationPanel) return;

        closeUserDropdown();

        notificationPanel.classList.add("show");

        if (notificationButton) {
            notificationButton.setAttribute(
                "aria-expanded",
                "true"
            );
        }
    }


    if (notificationButton) {

        notificationButton.addEventListener(
            "click",
            event => {

                event.stopPropagation();

                const isOpen =
                    notificationPanel.classList.contains(
                        "show"
                    );

                if (isOpen) {
                    closeNotificationPanel();
                } else {
                    openNotificationPanel();
                }

            }
        );

    }


    /* =====================================================
       MARK NOTIFICATIONS READ
    ===================================================== */

    if (markNotificationsRead) {

        markNotificationsRead.addEventListener(
            "click",
            () => {

                const unreadItems =
                    document.querySelectorAll(
                        ".notification-item.unread"
                    );

                unreadItems.forEach(item => {
                    item.classList.remove("unread");
                });


                const notificationDot =
                    document.querySelector(
                        ".notification-dot"
                    );

                if (notificationDot) {
                    notificationDot.style.display = "none";
                }


                const panelUnreadText =
                    notificationPanel?.querySelector(
                        ".panel-header span"
                    );

                if (panelUnreadText) {
                    panelUnreadText.textContent =
                        "All caught up";
                }


                showToast(
                    "All notifications marked as read.",
                    "success"
                );

            }
        );

    }


    /* =====================================================
       USER DROPDOWN
    ===================================================== */

    function closeUserDropdown() {

        if (!userDropdown) return;

        userDropdown.classList.remove("show");

        if (userProfileButton) {
            userProfileButton.setAttribute(
                "aria-expanded",
                "false"
            );
        }
    }


    function openUserDropdown() {

        if (!userDropdown) return;

        closeNotificationPanel();

        userDropdown.classList.add("show");

        if (userProfileButton) {
            userProfileButton.setAttribute(
                "aria-expanded",
                "true"
            );
        }
    }


    if (userProfileButton) {

        userProfileButton.addEventListener(
            "click",
            event => {

                event.stopPropagation();

                const isOpen =
                    userDropdown.classList.contains(
                        "show"
                    );

                if (isOpen) {
                    closeUserDropdown();
                } else {
                    openUserDropdown();
                }

            }
        );

    }


    /* =====================================================
       OUTSIDE CLICK
    ===================================================== */

    document.addEventListener(
        "click",
        event => {

            if (
                notificationPanel &&
                !notificationPanel.contains(event.target) &&
                notificationButton &&
                !notificationButton.contains(event.target)
            ) {
                closeNotificationPanel();
            }


            if (
                userDropdown &&
                !userDropdown.contains(event.target) &&
                userProfileButton &&
                !userProfileButton.contains(event.target)
            ) {
                closeUserDropdown();
            }

        }
    );


    /* =====================================================
       GLOBAL SEARCH
    ===================================================== */

    function openSearchResults(query = "") {

        if (!searchResultsOverlay) return;

        searchResultsOverlay.classList.add("show");

        if (searchResultTitle) {

            searchResultTitle.textContent =
                query
                    ? `Results for "${query}"`
                    : "Search HallMaster";
        }


        if (!query) {

            searchResultsContent.innerHTML = `

                <div class="search-empty">

                    <div class="search-empty-icon">

                        <svg width="26"
                             height="26"
                             viewBox="0 0 24 24"
                             fill="none">

                            <circle
                                cx="11"
                                cy="11"
                                r="7"
                                stroke="currentColor"
                                stroke-width="1.6"/>

                            <path
                                d="M16.5 16.5L21 21"
                                stroke="currentColor"
                                stroke-width="1.6"
                                stroke-linecap="round"/>

                        </svg>

                    </div>

                    <strong>
                        Search bookings, customers or invoices
                    </strong>

                    <span>
                        Start typing to search across HallMaster.
                    </span>

                </div>

            `;

            return;
        }


        /* Demo search results */

        const results = [

            {
                title: "Bookings",
                description:
                    "Search through venue bookings.",
                link: "bookings.html"
            },

            {
                title: "Customers",
                description:
                    "Find customer records and details.",
                link: "customers.html"
            },

            {
                title: "Invoices",
                description:
                    "Search invoices and payment records.",
                link: "invoices.html"
            },

            {
                title: "Payments",
                description:
                    "View payment activity and outstanding amounts.",
                link: "payments.html"
            }

        ];


        const filteredResults =
            results.filter(result => {

                const text =
                    `${result.title} ${result.description}`
                        .toLowerCase();

                return text.includes(
                    query.toLowerCase()
                );

            });


        if (filteredResults.length === 0) {

            searchResultsContent.innerHTML = `

                <div class="search-empty">

                    <div class="search-empty-icon">
                        ×
                    </div>

                    <strong>
                        No results found
                    </strong>

                    <span>
                        Try another search term.
                    </span>

                </div>

            `;

            return;
        }


        searchResultsContent.innerHTML =
            filteredResults.map(result => `

                <a href="${result.link}"
                   class="search-result-item"
                   style="
                       display:flex;
                       align-items:center;
                       gap:14px;
                       padding:14px;
                       margin-bottom:7px;
                       border:1px solid rgba(255,255,255,.06);
                       border-radius:11px;
                       background:rgba(255,255,255,.02);
                   ">

                    <div style="
                        width:36px;
                        height:36px;
                        display:grid;
                        place-items:center;
                        border-radius:9px;
                        background:rgba(201,169,110,.08);
                        color:#c9a96e;
                        font-size:11px;
                        font-weight:700;
                    ">
                        HM
                    </div>

                    <div>

                        <strong style="
                            display:block;
                            font-size:11px;
                            color:#f4f1eb;
                        ">
                            ${result.title}
                        </strong>

                        <span style="
                            display:block;
                            margin-top:4px;
                            font-size:9px;
                            color:#77736c;
                        ">
                            ${result.description}
                        </span>

                    </div>

                </a>

            `).join("");

    }


    if (globalSearch) {

        globalSearch.addEventListener(
            "click",
            () => {

                openSearchResults(
                    globalSearchInput?.value.trim() || ""
                );

            }
        );

    }


    if (globalSearchInput) {

        globalSearchInput.addEventListener(
            "focus",
            () => {

                if (window.innerWidth <= 800) {
                    openSearchResults();
                }

            }
        );


        globalSearchInput.addEventListener(
            "keydown",
            event => {

                if (event.key === "Enter") {

                    event.preventDefault();

                    openSearchResults(
                        globalSearchInput.value.trim()
                    );

                }

            }
        );


        globalSearchInput.addEventListener(
            "input",
            () => {

                const value =
                    globalSearchInput.value.trim();

                if (value.length >= 2) {

                    openSearchResults(value);

                }

            }
        );

    }


    /* =====================================================
       SEARCH SHORTCUT "/"
    ===================================================== */

    document.addEventListener(
        "keydown",
        event => {

            const activeElement =
                document.activeElement;

            const typing =
                activeElement &&
                (
                    activeElement.tagName === "INPUT" ||
                    activeElement.tagName === "TEXTAREA" ||
                    activeElement.isContentEditable
                );


            if (
                event.key === "/" &&
                !typing
            ) {

                event.preventDefault();

                if (globalSearchInput) {

                    globalSearchInput.focus();

                }

            }


            if (event.key === "Escape") {

                closeSearchResults();

                closeNotificationPanel();

                closeUserDropdown();

                closeSidebarMenu();

                closeModal();

            }

        }
    );


    /* =====================================================
       CLOSE SEARCH
    ===================================================== */

    function closeSearchResults() {

        if (!searchResultsOverlay) return;

        searchResultsOverlay.classList.remove("show");

    }


    if (closeSearchResultsButton) {

        closeSearchResultsButton.addEventListener(
            "click",
            closeSearchResults
        );

    }


    if (searchResultsOverlay) {

        searchResultsOverlay.addEventListener(
            "click",
            event => {

                if (
                    event.target ===
                    searchResultsOverlay
                ) {
                    closeSearchResults();
                }

            }
        );

    }


    /* =====================================================
       QUICK NEW BOOKING
    ===================================================== */

    if (quickActionButton) {

        quickActionButton.addEventListener(
            "click",
            () => {

                openModal(`

                    <div style="
                        padding:10px 5px 5px;
                    ">

                        <span style="
                            display:block;
                            color:#c9a96e;
                            font-size:9px;
                            font-weight:700;
                            letter-spacing:1.5px;
                            text-transform:uppercase;
                            margin-bottom:7px;
                        ">
                            Booking
                        </span>

                        <h2 style="
                            font-family:'Playfair Display',serif;
                            font-size:24px;
                            margin-bottom:20px;
                        ">
                            Create New Booking
                        </h2>


                        <div class="form-group">

                            <label class="form-label">
                                Customer Name
                            </label>

                            <input
                                class="form-control"
                                type="text"
                                placeholder="Enter customer name">

                        </div>


                        <div class="form-group">

                            <label class="form-label">
                                Event Date
                            </label>

                            <input
                                class="form-control"
                                type="date">

                        </div>


                        <div class="form-group">

                            <label class="form-label">
                                Hall
                            </label>

                            <select class="form-select">

                                <option>
                                    Select hall
                                </option>

                                <option>
                                    Hall A
                                </option>

                                <option>
                                    Hall B
                                </option>

                                <option>
                                    Grand Ballroom
                                </option>

                            </select>

                        </div>


                        <div style="
                            display:flex;
                            justify-content:flex-end;
                            gap:8px;
                            margin-top:22px;
                        ">

                            <button
                                class="btn btn-secondary"
                                onclick="closeModal()">

                                Cancel

                            </button>

                            <button
                                class="btn btn-primary"
                                onclick="
                                    closeModal();
                                    showToast(
                                        'Booking created successfully.',
                                        'success'
                                    );
                                ">

                                Create Booking

                            </button>

                        </div>

                    </div>

                `);

            }
        );

    }


    /* =====================================================
       MODAL
    ===================================================== */

    function openModal(content) {

        if (!globalModal) return;

        if (modalContent) {
            modalContent.innerHTML = content;
        }

        globalModal.classList.add("show");

        globalModal.setAttribute(
            "aria-hidden",
            "false"
        );

        document.body.style.overflow = "hidden";

    }


    function closeModal() {

        if (!globalModal) return;

        globalModal.classList.remove("show");

        globalModal.setAttribute(
            "aria-hidden",
            "true"
        );

        document.body.style.overflow = "";

    }


    window.openModal = openModal;
    window.closeModal = closeModal;


    if (modalClose) {

        modalClose.addEventListener(
            "click",
            closeModal
        );

    }


    if (globalModal) {

        globalModal.addEventListener(
            "click",
            event => {

                if (
                    event.target === globalModal
                ) {
                    closeModal();
                }

            }
        );

    }


    /* =====================================================
       LOGOUT
    ===================================================== */

    if (logoutButton) {

        logoutButton.addEventListener(
            "click",
            () => {

                closeUserDropdown();

                openModal(`

                    <div style="
                        text-align:center;
                        padding:15px 5px 5px;
                    ">

                        <div style="
                            width:55px;
                            height:55px;
                            margin:0 auto 16px;
                            display:grid;
                            place-items:center;
                            border-radius:16px;
                            background:rgba(229,115,115,.08);
                            color:#df8585;
                            font-size:20px;
                        ">
                            !
                        </div>

                        <h2 style="
                            font-family:'Playfair Display',serif;
                            font-size:23px;
                        ">
                            Sign Out?
                        </h2>

                        <p style="
                            margin-top:8px;
                            color:#77736c;
                            font-size:10px;
                            line-height:1.6;
                        ">
                            Are you sure you want to sign out
                            from HallMaster?
                        </p>

                        <div style="
                            display:flex;
                            justify-content:center;
                            gap:8px;
                            margin-top:23px;
                        ">

                            <button
                                class="btn btn-secondary"
                                onclick="closeModal()">

                                Cancel

                            </button>

                            <button
                                class="btn"
                                style="
                                    background:#5b2727;
                                    color:#f1b2b2;
                                "
                                onclick="
                                    closeModal();
                                    showToast(
                                        'Signed out successfully.',
                                        'success'
                                    );
                                ">

                                Sign Out

                            </button>

                        </div>

                    </div>

                `);

            }
        );

    }


    /* =====================================================
       TOAST
    ===================================================== */

    function showToast(
        message,
        type = "info",
        duration = 3500
    ) {

        if (!toastContainer) return;


        const toast =
            document.createElement("div");

        toast.className =
            `toast ${type}`;


        toast.innerHTML = `

            <span>
                ${message}
            </span>

        `;


        toastContainer.appendChild(toast);


        setTimeout(() => {

            toast.style.animation =
                "toastOut .3s ease forwards";

            setTimeout(() => {

                toast.remove();

            }, 300);

        }, duration);

    }


    window.showToast = showToast;


    /* =====================================================
       DATE
    ===================================================== */

    function updateDate() {

        if (!currentDate) return;


        const now = new Date();


        const options = {
            weekday: "long",
            month: "long",
            day: "numeric",
            year: "numeric"
        };


        currentDate.textContent =
            now.toLocaleDateString(
                "en-US",
                options
            );

    }


    updateDate();


    /* =====================================================
       GREETING
    ===================================================== */

    function updateGreeting() {

        if (!greeting) return;


        const hour =
            new Date().getHours();


        let message;


        if (hour < 12) {

            message = "Good morning, Faisal";

        } else if (hour < 17) {

            message = "Good afternoon, Faisal";

        } else {

            message = "Good evening, Faisal";

        }


        greeting.textContent = message;

    }


    updateGreeting();


    /* =====================================================
       WINDOW RESIZE
    ===================================================== */

    let previousWidth =
        window.innerWidth;


    window.addEventListener(
        "resize",
        () => {

            const currentWidth =
                window.innerWidth;


            /*
                When moving from mobile
                to desktop, reset mobile sidebar.
            */

            if (
                previousWidth <= 800 &&
                currentWidth > 800
            ) {

                closeSidebarMenu();

            }


            previousWidth =
                currentWidth;

        }
    );


    /* =====================================================
       PREVENT BODY SCROLL WHEN MODAL IS OPEN
    ===================================================== */

    const observer =
        new MutationObserver(() => {

            if (
                globalModal &&
                globalModal.classList.contains("show")
            ) {

                document.body.style.overflow =
                    "hidden";

            }

        });


    if (globalModal) {

        observer.observe(
            globalModal,
            {
                attributes: true,
                attributeFilter: ["class"]
            }
        );

    }


    /* =====================================================
       INITIAL STATE
    ===================================================== */

    closeNotificationPanel();
    closeUserDropdown();

});
