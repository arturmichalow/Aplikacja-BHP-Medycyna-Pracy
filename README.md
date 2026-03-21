# Aplikacja BHP / medycyna pracy

Gotowa aplikacja webowa w Pythonie oparta o Streamlit i SQLite.

## Co zawiera
- ekran logowania z tłem graficznym,
- Dashboard z licznikami i kalendarzem badań do 30 dni,
- Przypomnienia i alerty: po terminie / do 30 dni / brak daty,
- Baza pracowników i szybki podgląd zagrożeń,
- Panel pracownika z historią badań,
- Nowe skierowanie z generowaniem PDF na bazie wzoru,
- Lista skierowań z pobraniem i podglądem PDF,
- Mapa zagrożeń importowana z pliku `LMP.xlsm`,
- Import danych z Excela,
- Eksporty do Excel,
- Użytkownicy i role z blokowaniem, odblokowaniem, resetem hasła i uprawnieniami.

## Uruchomienie
```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

## Dane startowe
- login: `admin`
- hasło: `Admin123!@#`

Dodatkowe konta:
- `bhp` / `Bhp123!@#45`
- `hr` / `Hr123!@#45`
- `podglad` / `Podglad123!@#`

## Pliki wejściowe
- wzór PDF skierowania: `assets/skierowanie_template.pdf`
- domyślna mapa zagrożeń: `assets/LMP.xlsm`

## Uwagi
- PESEL przy tworzeniu skierowania dopuszcza wyłącznie cyfry.
- Zagrożenia można usuwać i dopisywać ręcznie.
- Na PDF druga strona grupuje zagrożenia do sekcji I-V.
- Numer skierowania nadawany jest automatycznie w formacie `numer/miesiąc/rok`.
