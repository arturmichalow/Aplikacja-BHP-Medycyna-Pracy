from __future__ import annotations
import os
import json
import base64
from pathlib import Path
from datetime import date, datetime, timedelta

import streamlit as st
import pandas as pd

from app import db
from app.ui import inject_css, render_banner, status_badge
from app.export_utils import df_to_excel_bytes
from app.docx_utils import generate_referral_docx

st.set_page_config(page_title="Aplikacja BHP / medycyna pracy", layout="wide")
inject_css()
db.init_db()

PAGES = [
    "Dashboard",
    "Przypomnienia i alerty",
    "Baza pracowników",
    "Panel pracownika",
    "Nowe skierowanie",
    "Lista skierowań",
    "Mapa zagrożeń",
    "Import danych",
    "Eksporty",
    "Bezpieczeństwo i konto",
    "Użytkownicy i role",
]

PERM_MAP = {
    "Dashboard": "view_dashboard",
    "Przypomnienia i alerty": "view_alerts",
    "Baza pracowników": "view_employee_db",
    "Panel pracownika": "view_employee_panel",
    "Nowe skierowanie": "create_referrals",
    "Lista skierowań": "view_referrals",
    "Mapa zagrożeń": "view_hazard_map",
    "Import danych": "import_data",
    "Eksporty": "export_data",
    "Bezpieczeństwo i konto": "security_center",
    "Użytkownicy i role": "manage_users",
}

SECTION_OPTIONS = db.SECTION_OPTIONS


def init_state():
    st.session_state.setdefault("page", "Dashboard")
    st.session_state.setdefault("selected_referral_id", None)
    st.session_state.setdefault("last_docx", None)
    st.session_state.setdefault("last_referral_number", None)


def login_screen():
    st.markdown("<div class='login-wrap'>", unsafe_allow_html=True)

    # LOGO
    st.markdown(
        "<div class='login-logo-bar'><div class='login-logo'></div></div>",
        unsafe_allow_html=True
    )

    # FORMULARZ
    st.markdown("<div class='login-card'>", unsafe_allow_html=True)
    st.markdown("<h3>Bezpieczne logowanie do aplikacji</h3>", unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        login = st.text_input("Login", value="admin")
        password = st.text_input("Hasło", type="password", value="Admin123!@#")
        submitted = st.form_submit_button("Zaloguj")

    if submitted:
        user, error = db.authenticate(login, password)
        if error:
            st.error(error)
        else:
            st.session_state["user"] = user
            db.log_action(user["login"], "LOGOWANIE", "Udane logowanie")
            st.rerun()

    st.caption("Dane startowe: admin / Admin123!@#")

    st.markdown("</div></div>", unsafe_allow_html=True)


def sidebar_menu(user):
    with st.sidebar:
        st.markdown("### Nawigacja")
        st.write(f"Użytkownik: {user['full_name']}")
        st.write(f"Rola: {user['role']}")

        perms = user.get("permissions", {})
        for page in PAGES:
            if not perms.get(PERM_MAP.get(page, ""), True):
                continue

            cls = "menu-btn menu-active" if st.session_state.page == page else "menu-btn"
            with st.container():
                st.markdown(f"<div class='{cls}'>", unsafe_allow_html=True)
                if st.button(page, key=f"menu_{page}", use_container_width=True):
                    st.session_state.page = page
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        if st.button("Wyloguj", key="logout_btn"):
            db.log_action(user["login"], "WYLOGOWANIE", "Użytkownik wylogowany")
            st.session_state.clear()
            st.rerun()


def dashboard_page(user):
    df = db.get_employees_df()
    today = date.today()

    due_7 = int((df["dni_do_badan"].fillna(9999).between(0, 7)).sum()) if not df.empty else 0
    due_30 = int((df["dni_do_badan"].fillna(9999).between(0, 30)).sum()) if not df.empty else 0
    overdue = int((df["dni_do_badan"].fillna(9999) < 0).sum()) if not df.empty else 0
    no_date = int(df["next_exam_date"].isna().sum()) if not df.empty else 0

    this_month = 0
    if not df.empty:
        this_month = int(
            df["next_exam_date"].fillna("").apply(
                lambda x: str(x).startswith(f"{today.year}-{today.month:02d}")
            ).sum()
        )

    cols = st.columns(5)
    metrics = [
        ("Po terminie", overdue),
        ("Do 7 dni", due_7),
        ("Do 30 dni", due_30),
        ("W tym miesiącu", this_month),
        ("Brak daty", no_date),
    ]

    for c, (label, val) in zip(cols, metrics):
        c.markdown(
            f"<div class='metric-card'><div style='font-size:13px;color:#64748b'>{label}</div>"
            f"<div style='font-size:28px;font-weight:800'>{val}</div></div>",
            unsafe_allow_html=True,
        )

    left, right = st.columns([1.25, 1])

    with left:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.subheader("Priorytety na dziś")
        st.warning(f"Po terminie: {overdue} pracowników")
        st.info(f"Kończą się w 30 dni: {due_30} pracowników")
        st.subheader("Kalendarz badań (najbliższe 30 dni)")

        cal = df[df["dni_do_badan"].fillna(9999).between(0, 30)].copy() if not df.empty else pd.DataFrame()
        if not cal.empty:
            cal = cal[["full_name", "department_name", "position_name", "next_exam_date", "dni_do_badan", "status"]]
            cal.columns = ["Imię i nazwisko", "Dział", "Stanowisko", "Następne badanie", "Dni do badań", "Status"]
            st.dataframe(cal, use_container_width=True, hide_index=True)
        else:
            st.success("Brak pozycji w najbliższych 30 dniach.")

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.subheader("Status badań")
        status_counts = (
            df["status"].fillna("BRAK DATY").value_counts().rename_axis("status").reset_index(name="liczba")
            if not df.empty
            else pd.DataFrame(columns=["status", "liczba"])
        )
        st.dataframe(status_counts, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)


def alerts_page():
    df = db.get_employees_df()

    tab1, tab2, tab3 = st.tabs(["Po terminie", "Do 30 dni", "Brak daty"])
    tables = {
        "Po terminie": df[df["dni_do_badan"].fillna(9999) < 0].copy() if not df.empty else pd.DataFrame(),
        "Do 30 dni": df[df["dni_do_badan"].fillna(9999).between(0, 30)].copy() if not df.empty else pd.DataFrame(),
        "Brak daty": df[df["next_exam_date"].isna()].copy() if not df.empty else pd.DataFrame(),
    }

    for label, tab in zip(tables.keys(), [tab1, tab2, tab3]):
        with tab:
            t = tables[label]
            if not t.empty:
                show = t[["full_name", "department_name", "position_name", "next_exam_date", "dni_do_badan", "status"]]
                show.columns = ["Imię i nazwisko", "Dział", "Stanowisko", "Następne badanie", "Dni do badań", "Status"]
                st.dataframe(show, use_container_width=True, hide_index=True)
                bytes_ = df_to_excel_bytes({label: show})
                st.download_button(f"Eksportuj {label.lower()} do Excel", bytes_, file_name=f"{label}.xlsx")
            else:
                st.success(f"Brak pozycji: {label.lower()}.")


def employee_db_page():
    df = db.get_employees_df()
    if df.empty:
        st.info("Brak pracowników.")
        return

    show = df[
        ["full_name", "department_name", "position_name", "pesel", "last_exam_date", "next_exam_date", "dni_do_badan", "status"]
    ].copy()
    show.columns = ["Imię i nazwisko", "Dział", "Stanowisko", "PESEL", "Ostatnie badanie", "Następne badanie", "Dni do badań", "Status"]
    st.dataframe(show, use_container_width=True, hide_index=True)

    excel = df_to_excel_bytes({"Baza pracowników": show})
    st.download_button("Eksportuj bazę pracowników do Excel", excel, file_name="baza_pracownikow.xlsx")

    st.subheader("Szybki podgląd zagrożeń stanowiska")
    name = st.selectbox("Podgląd dla pracownika", options=df["full_name"].tolist())
    row = df[df["full_name"] == name].iloc[0]
    hz = db.get_hazards(row["department_name"], row["position_name"])
    if not hz.empty:
        st.dataframe(hz[["Zagrożenie", "Kategoria", "Opis warunków pracy"]], use_container_width=True, hide_index=True)


def employee_panel_page():
    df = db.get_employees_df()
    if df.empty:
        st.info("Brak pracowników")
        return

    def _parse_date(value):
        if value is None or value == "":
            return None
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
                try:
                    return datetime.strptime(value, fmt).date()
                except Exception:
                    pass
        try:
            return value
        except Exception:
            return None

    search = st.text_input("Wybierz pracownika", placeholder="Wpisz imię lub nazwisko...")
    opts = (
        df[df["full_name"].str.contains(search, case=False, na=False)]["full_name"].tolist()
        if search
        else df["full_name"].tolist()
    )

    if not opts:
        st.warning("Nie znaleziono pracownika.")
        return

    name = st.selectbox("Lista pracowników", options=opts, label_visibility="collapsed")
    row = df[df["full_name"] == name].iloc[0]

    with st.form("employee_edit_form"):
        c1, c2 = st.columns(2)

        full_name = c1.text_input("Imię i nazwisko", value=row["full_name"] or "")
        department_name = c2.text_input("Dział", value=row["department_name"] or "")
        position_name = c1.text_input("Stanowisko", value=row["position_name"] or "")
        pesel = c2.text_input("PESEL", value=row["pesel"] or "")
        address = st.text_input("Adres", value=row["address"] or "")

        c3, c4 = st.columns(2)
        last_exam_value = _parse_date(row["last_exam_date"])
        next_exam_value = _parse_date(row["next_exam_date"])

        last_exam_date = c3.date_input(
            "Ostatnie badanie",
            value=last_exam_value,
            format="YYYY-MM-DD",
        )
        next_exam_date = c4.date_input(
            "Następne badanie",
            value=next_exam_value,
            format="YYYY-MM-DD",
        )

        submitted = st.form_submit_button("Zapisz zmiany")

    if submitted:
        if pesel and not str(pesel).isdigit():
            st.error("PESEL może zawierać wyłącznie cyfry.")
        else:
            db.update_employee(
                employee_id=int(row["id"]),
                full_name=full_name.strip(),
                department_name=department_name.strip(),
                position_name=position_name.strip(),
                pesel=str(pesel).strip(),
                address=address.strip(),
                last_exam_date=last_exam_date.isoformat() if last_exam_date else None,
                next_exam_date=next_exam_date.isoformat() if next_exam_date else None,
            )
            st.success("Zapisano zmiany.")
            st.rerun()

    refreshed_df = db.get_employees_df()
    refreshed_row = refreshed_df[refreshed_df["id"] == row["id"]].iloc[0]

    c1, c2 = st.columns([1, 1.1])

    with c1:
        st.markdown(f"**Pracownik:** {refreshed_row['full_name']}")
        st.markdown(f"**Dział:** {refreshed_row['department_name']}")
        st.markdown(f"**Stanowisko:** {refreshed_row['position_name']}")
        st.markdown(f"**PESEL:** {refreshed_row['pesel'] or '-'}")
        st.markdown(f"**Adres:** {refreshed_row['address'] or '-'}")
        st.markdown(f"**Ostatnie badanie:** {refreshed_row['last_exam_date'] or '-'}")
        st.markdown(f"**Następne badanie:** {refreshed_row['next_exam_date'] or '-'}")
        st.markdown(f"**Status:** {refreshed_row['status']}")
        st.markdown(
            f"**Do końca badań:** "
            f"{refreshed_row['dni_do_badan'] if refreshed_row['dni_do_badan'] is not None else '-'} dni"
        )

    with c2:
        hz = db.get_hazards(refreshed_row["department_name"], refreshed_row["position_name"])
        st.markdown("**Zagrożenia na stanowisku**")
        if not hz.empty:
            st.dataframe(
                hz[["Zagrożenie", "Kategoria"]],
                use_container_width=True,
                hide_index=True,
            )

    refs = db.get_referrals_df()
    if not refs.empty:
        hist = refs[refs["employee_name"] == refreshed_row["full_name"]][
            ["issue_date", "exam_type", "next_exam_date", "status"]
        ].copy()
        hist.columns = ["Data wystawienia", "Rodzaj badania", "Następne badanie", "Status"]
        st.markdown("### Historia badań")
        st.dataframe(hist, use_container_width=True, hide_index=True)


def _hazards_editor(default_df: pd.DataFrame) -> list[dict]:
    editor = default_df.copy() if not default_df.empty else pd.DataFrame(
        columns=["hazard_name", "category", "section_label", "work_conditions"]
    )

    edited = st.data_editor(
        editor,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "hazard_name": st.column_config.TextColumn("Zagrożenie", required=True, width="large"),
            "category": st.column_config.SelectboxColumn(
                "Kategoria",
                options=["CZYNNIKI FIZYCZNE", "PYŁY", "CZYNNIKI CHEMICZNE", "CZYNNIKI BIOLOGICZNE", "INNE"],
                width="medium",
            ),
            "section_label": st.column_config.SelectboxColumn(
                "Sekcja PDF",
                options=SECTION_OPTIONS,
                width="medium",
            ),
            "work_conditions": st.column_config.TextColumn(
                "Opis warunków pracy",
                width="large",
            ),
        },
        hide_index=True,
        key="hazards_editor",
    )

    edited = edited.fillna("")
    edited = edited[edited["hazard_name"].astype(str).str.strip() != ""]
    return edited.to_dict("records")


def new_referral_page(user):
    emps = db.get_employees_df()
    mode = st.radio("Tryb", ["Istniejący pracownik", "Nowy pracownik"], horizontal=True)
    selected_emp = None

    if mode == "Istniejący pracownik" and not emps.empty:
        search = st.text_input("Pracownik", placeholder="Wpisz nazwisko...")
        filtered = emps[emps["full_name"].str.contains(search, case=False, na=False)] if search else emps

        if filtered.empty:
            st.warning("Nie znaleziono pracownika o takim imieniu lub nazwisku.")
            default_name = ""
            default_dep = db.get_departments()[0] if db.get_departments() else ""
            default_pos = ""
            pesel = ""
            address = ""
        else:
            emp_name = st.selectbox("Lista pracowników", filtered["full_name"].tolist(), label_visibility="collapsed")
            selected_emp = filtered[filtered["full_name"] == emp_name].iloc[0]

            default_name = selected_emp["full_name"]
            default_dep = selected_emp["department_name"]
            default_pos = selected_emp["position_name"]
            pesel = selected_emp["pesel"] or ""
            address = selected_emp["address"] or ""
    else:
        departments = db.get_departments()
        default_name = ""
        default_dep = departments[0] if departments else ""
        default_pos = ""
        pesel = ""
        address = ""
    name = st.text_input("Imię i nazwisko", value=default_name)

    deps = db.get_departments() or ["BHP"]
    dep = st.selectbox("Dział", deps, index=max(0, deps.index(default_dep)) if default_dep in deps else 0)

    pos_list = db.get_positions(dep) or [""]
    pos = st.selectbox("Stanowisko", pos_list, index=max(0, pos_list.index(default_pos)) if default_pos in pos_list else 0)

    c1, c2 = st.columns(2)
    issue_date = c1.date_input("Data wystawienia", value=date.today(), format="YYYY/MM/DD")
    exam_type = c2.selectbox("Rodzaj badania", ["wstępne", "okresowe", "kontrolne"])

    c3, c4 = st.columns(2)
    c3.text_input(
        "Następne badanie",
        value="",
        disabled=True,
        placeholder="Ustawiane później w panelu pracownika",
    )
    employer = c4.text_input("Oznaczenie pracodawcy", value="SAFETY Service")

    c5, c6 = st.columns(2)
    pesel_value = c5.text_input("PESEL", value=pesel)
    address_value = c6.text_input("Adres pracownika", value=address)

    place = st.text_input("Miejscowość wystawienia skierowania", value="Warszawa")

    hazard_df = db.get_hazards(dep, pos)

    if not hazard_df.empty:
        work_conditions_series = (
            hazard_df["Opis warunków pracy"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        unique_conditions = [x for x in work_conditions_series.unique().tolist() if x]

        default_position_description = "\n".join(unique_conditions) if unique_conditions else pos

        auto_df = hazard_df[["Zagrożenie", "Kategoria", "Sekcja", "Opis warunków pracy"]].copy()
        auto_df.columns = ["hazard_name", "category", "section_label", "work_conditions"]
    else:
        default_position_description = pos
        auto_df = pd.DataFrame(columns=["hazard_name", "category", "section_label", "work_conditions"])

    position_description = st.text_area(
        "Określenie stanowiska/stanowisk pracy",
        value=default_position_description,
        height=130,
        help="To pole trafia do dokumentu Word w sekcji 'określenie stanowiska/stanowisk pracy'.",
    )

    st.markdown("### Automatycznie pobrane zagrożenia")
    hazards = _hazards_editor(auto_df)

    if st.button("Zapisz i wygeneruj dokument Word", type="primary"):
        if not name.strip():
            st.error("Podaj imię i nazwisko.")
        elif pesel_value and (not pesel_value.isdigit()):
            st.error("PESEL może zawierać wyłącznie cyfry.")
        elif not dep or not pos:
            st.error("Wybierz dział i stanowisko.")
        else:
            payload = {
                "employee_id": int(selected_emp["id"]) if selected_emp is not None else None,
                "employee_name": name.strip(),
                "department_name": dep,
                "position_name": pos,
                "position_description": position_description.strip(),
                "issue_date": issue_date.isoformat(),
                "next_exam_date": None,
                "exam_type": exam_type,
                "employer": employer.strip(),
                "pesel": pesel_value.strip(),
                "employee_address": address_value.strip(),
                "place_of_issue": place.strip(),
            }

            rid = db.create_referral(payload, hazards, user["login"])
            referral = db.get_referral(rid)
            docx_path = generate_referral_docx(referral)

            db.update_referral_pdf_path(rid, docx_path)

            st.session_state["last_docx"] = docx_path
            st.session_state["last_referral_number"] = referral["referral_number"]
            st.success(f"Zapisano skierowanie {referral['referral_number']} {referral['employee_name']}")

    if st.session_state.get("last_docx"):
        docx_path = st.session_state["last_docx"]
        if os.path.exists(docx_path):
            with open(docx_path, "rb") as f:
                data = f.read()

            st.download_button(
                "Pobierz dokument Word",
                data,
                file_name=os.path.basename(docx_path),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            st.info("Podgląd Word w przeglądarce nie jest stabilny, więc tutaj zostawiam pobieranie pliku.")
def referrals_page():
    df = db.get_referrals_df()
    if df.empty:
        st.info("Brak skierowań.")
        return

    c1, c2, c3, c4 = st.columns(4)
    emp_filter = c1.selectbox("Pracownik", ["Wszyscy"] + sorted(df["employee_name"].dropna().unique().tolist()))
    dep_filter = c2.selectbox("Dział", ["Wszystkie"] + sorted(df["department_name"].dropna().unique().tolist()))
    status_filter = c3.selectbox("Status", ["Wszystkie"] + sorted(df["status"].dropna().unique().tolist()))
    type_filter = c4.selectbox("Rodzaj badania", ["Wszystkie"] + sorted(df["exam_type"].dropna().unique().tolist()))

    f = df.copy()
    if emp_filter != "Wszyscy":
        f = f[f["employee_name"] == emp_filter]
    if dep_filter != "Wszystkie":
        f = f[f["department_name"] == dep_filter]
    if status_filter != "Wszystkie":
        f = f[f["status"] == status_filter]
    if type_filter != "Wszystkie":
        f = f[f["exam_type"] == type_filter]

    for _, row in f.iterrows():
        cols = st.columns([1.3, 1.1, 1.0, 1.2, 1.6, 1.0, 1.0, 1.0, 1.0])

        vals = [
            row["referral_number"],
            row["employee_name"],
            row["issue_date"],
            row["department_name"],
            row["position_name"],
            row["exam_type"],
            row["next_exam_date"] or "-",
            row["status"],
        ]
        labels = ["Numer", "Imię i nazwisko", "Data wystawienia", "Dział", "Stanowisko", "Rodzaj", "Następne badanie", "Status"]

        for c, v, lab in zip(cols[:-1], vals, labels):
            c.markdown(f"**{lab}:** {v}")

        action_col = cols[-1]
        with action_col:
            doc_path = row["pdf_path"]
            if doc_path and os.path.exists(doc_path):
                data = Path(doc_path).read_bytes()
                filename = os.path.basename(doc_path)
                mime = (
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    if filename.lower().endswith(".docx")
                    else "application/octet-stream"
                )
                st.download_button(
                    "Pobierz plik",
                    data,
                    file_name=filename,
                    key=f"dl_{row['id']}",
                    mime=mime,
                )

        st.divider()

    out = df_to_excel_bytes({
        "Lista skierowań": f[
            ["referral_number", "employee_name", "issue_date", "department_name", "position_name", "exam_type", "next_exam_date", "status"]
        ]
    })
    st.download_button("Eksportuj listę skierowań do Excel", out, file_name="lista_skierowan.xlsx")


def hazard_map_page():
    conn = db.get_connection()
    hz = pd.read_sql_query(
        'SELECT department_name AS Dział, position_name AS Stanowisko, hazard_name AS Zagrożenie, category AS Kategoria, work_conditions AS "Opis warunków pracy" FROM hazard_map',
        conn,
    )
    conn.close()

    deps = ["Wszystkie"] + sorted(hz["Dział"].dropna().unique().tolist()) if not hz.empty else ["Wszystkie"]
    dep = st.selectbox("Dział", deps)

    pos_opts = ["Wszystkie"] + (
        sorted(hz[hz["Dział"] == dep]["Stanowisko"].dropna().unique().tolist())
        if dep != "Wszystkie"
        else sorted(hz["Stanowisko"].dropna().unique().tolist())
    )
    pos = st.selectbox("Stanowisko", pos_opts)

    filtered = hz.copy()
    if dep != "Wszystkie":
        filtered = filtered[filtered["Dział"] == dep]
    if pos != "Wszystkie":
        filtered = filtered[filtered["Stanowisko"] == pos]

    st.dataframe(filtered, use_container_width=True, hide_index=True)
    out = df_to_excel_bytes({"Mapa zagrożeń": filtered})
    st.download_button("Eksportuj mapę zagrożeń do Excel", out, file_name="mapa_zagrozen.xlsx")


def import_page(user):
    st.write("Wgraj plik .xlsx lub .xlsm")
    uploaded = st.file_uploader("Plik mapy zagrożeń", type=["xlsx", "xlsm"])

    if uploaded is not None and st.button("Importuj plik"):
        tmp = Path("data") / uploaded.name
        tmp.write_bytes(uploaded.getvalue())
        count = db.import_hazard_map(tmp, replace=True)
        db.log_action(user["login"], "IMPORT_DANYCH", f"Import pliku {uploaded.name}")
        st.success(f"Zaimportowano {count} rekordów mapy zagrożeń.")

    if st.button("Przetaduj dane z domyślnego pliku LMP.xlsm"):
        count = db.import_hazard_map(Path("assets/LMP.xlsm"), replace=True)
        st.success(f"Wczytano {count} rekordów z pliku domyślnego.")


def exports_page():
    emp = db.get_employees_df()
    refs = db.get_referrals_df()
    audit = db.get_audit_df()

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "Pełna baza pracowników",
            df_to_excel_bytes({"Pracownicy": emp}),
            file_name="pracownicy_pelna_baza.xlsx",
        )

        overdue = emp[emp["status"] == "PO TERMINIE"] if not emp.empty else emp
        st.download_button(
            "Pracownicy po terminie",
            df_to_excel_bytes({"Po terminie": overdue}),
            file_name="pracownicy_po_terminie.xlsx",
        )

        conn = db.get_connection()
        hz = pd.read_sql_query("SELECT * FROM hazard_map", conn)
        conn.close()

        st.download_button(
            "Mapa zagrożeń",
            df_to_excel_bytes({"Mapa zagrożeń": hz}),
            file_name="mapa_zagrozen.xlsx",
        )
        st.download_button(
            "Historia zmian",
            df_to_excel_bytes({"Audit": audit}),
            file_name="historia_zmian.xlsx",
        )

    with col2:
        due30 = emp[emp["dni_do_badan"].fillna(9999).between(0, 30)] if not emp.empty else emp
        st.download_button(
            "Badania do 30 dni",
            df_to_excel_bytes({"Do 30 dni": due30}),
            file_name="badania_30_dni.xlsx",
        )
        st.download_button(
            "Rejestr skierowań",
            df_to_excel_bytes({"Skierowania": refs}),
            file_name="rejestr_skierowan.xlsx",
        )


def security_page(user):
    st.subheader("Bezpieczeństwo i konto")
    st.info("Ta sekcja może zawierać w przyszłości kopie zapasowe i dodatkowe ustawienia bezpieczeństwa.")
    st.write(f"Zalogowano jako: **{user['full_name']}** ({user['role']})")

    audit = db.get_audit_df().head(20)
    st.markdown("### Ostatnie zdarzenia")
    st.dataframe(audit, use_container_width=True, hide_index=True)


def users_page(user):
    users = db.get_users_df()

    with st.form("create_user_form"):
        st.subheader("Dodaj użytkownika")
        cc1, cc2 = st.columns(2)
        login = cc1.text_input("Login nowego użytkownika")
        full_name = cc2.text_input("Imię i nazwisko")

        cc3, cc4 = st.columns(2)
        temp_pass = cc3.text_input("Hasło tymczasowe", type="password")
        role = cc4.selectbox("Rola", list(db.ROLE_PRESETS.keys()))

        if st.form_submit_button("Dodaj użytkownika"):
            try:
                db.create_user(login, full_name, role, temp_pass)
                db.log_action(user["login"], "DODANO_UZYTKOWNIKA", login)
                st.success("Dodano użytkownika.")
                st.rerun()
            except Exception as e:
                st.error(f"Nie udało się dodać użytkownika: {e}")

    st.subheader("Lista użytkowników")
    show = users[
        ["id", "login", "full_name", "role", "active", "last_login", "failed_attempts", "blocked_until", "permissions_json"]
    ].copy() if not users.empty else pd.DataFrame()

    if not show.empty:
        show.columns = [
            "ID",
            "Login",
            "Imię i nazwisko",
            "Rola",
            "Status",
            "Ostatnie logowanie",
            "Błędne próby",
            "Blokada do",
            "Uprawnienia JSON",
        ]
        show["Status"] = show["Status"].map({1: "Aktywny", 0: "Nieaktywny"})
        st.dataframe(show, use_container_width=True, hide_index=True)

        selected = st.selectbox("Zarządzaj użytkownikiem", users["login"].tolist())
        row = users[users["login"] == selected].iloc[0]

        active = st.toggle("Aktywny", value=bool(row["active"]))
        c1, c2 = st.columns(2)

        if c1.button("Zapisz status użytkownika"):
            db.set_user_active(int(row["id"]), active)
            st.success("Zapisano status.")
            st.rerun()

        if c2.button("Odblokuj konto"):
            db.unlock_user(int(row["id"]))
            st.success("Konto odblokowane.")
            st.rerun()

        st.markdown("### Uprawnienia szczegółowe")
        perms = json.loads(row["permissions_json"])
        updated = {}
        cols = st.columns(2)

        perm_labels = {
            "export_data": "Eksport danych",
            "edit_workers": "Edycja pracowników",
            "create_referrals": "Nowe skierowania",
            "manage_users": "Zarządzanie użytkownikami",
            "view_alerts": "Alerty i przypomnienia",
            "view_dashboard": "Dashboard",
            "view_employee_panel": "Panel pracownika",
            "view_hr": "Panel HR",
            "import_data": "Import danych",
            "security_center": "Własne konto i bezpieczeństwo",
            "security_center_2": "Centrum bezpieczeństwa",
            "backup": "Przywracanie backupu",
            "history": "Historia zmian",
            "view_employee_db": "Baza pracowników",
            "view_hazard_map": "Mapa zagrożeń",
            "view_referrals": "Lista skierowań",
        }

        keys = [
            "export_data",
            "create_referrals",
            "manage_users",
            "view_alerts",
            "view_dashboard",
            "view_employee_panel",
            "import_data",
            "history",
            "view_employee_db",
            "view_hazard_map",
            "view_referrals",
            "security_center",
        ]

        for idx, k in enumerate(keys):
            updated[k] = cols[idx % 2].checkbox(
                perm_labels.get(k, k),
                value=bool(perms.get(k, False)),
                key=f"perm_{k}",
            )

        if st.button("Zapisz uprawnienia"):
            db.set_user_permissions(int(row["id"]), updated)
            st.success("Uprawnienia zapisane.")
            st.rerun()

        new_pass = st.text_input("Nowe hasło tymczasowe", type="password")
        if st.button("Zresetuj hasło"):
            db.reset_user_password(int(row["id"]), new_pass)
            st.success("Hasło zresetowane.")


def main():
    init_state()

    if "user" not in st.session_state:
        login_screen()
        return

    user = st.session_state["user"]
    sidebar_menu(user)

    emp = db.get_employees_df()
    refs = db.get_referrals_df()
    render_banner(user, len(emp), len(refs))

    page = st.session_state.page
    st.subheader(page)

    if page == "Dashboard":
        dashboard_page(user)
    elif page == "Przypomnienia i alerty":
        alerts_page()
    elif page == "Baza pracowników":
        employee_db_page()
    elif page == "Panel pracownika":
        employee_panel_page()
    elif page == "Nowe skierowanie":
        new_referral_page(user)
    elif page == "Lista skierowań":
        referrals_page()
    elif page == "Mapa zagrożeń":
        hazard_map_page()
    elif page == "Import danych":
        import_page(user)
    elif page == "Eksporty":
        exports_page()
    elif page == "Bezpieczeństwo i konto":
        security_page(user)
    elif page == "Użytkownicy i role":
        users_page(user)


if __name__ == "__main__":
    main()