// Enkel, avhengighetsfri søkbar dropdown (combobox) for malt/humle/gjær/stil.
// Starter blank, filtrerer på delvis tekst, navigerbar med tastatur, og store
// nok trykkflater til å fungere godt på touch. Ingen ekstern autocomplete-lib.

// Modulnivå-teller (ikke per instans) -- garanterer unike listbox-/option-id-er
// på tvers av ALLE samtidig monterte Combobox-instanser (f.eks. flere
// malt-/humle-rader), ikke bare unike innad i én instans.
let comboboxInstansTeller = 0;

class Combobox {
  constructor({ items, placeholder = "", ariaLabel = "", onSelect = () => {} }) {
    this.items = items; // [{ id, label, search?, group? }] -- "search" (lowercase) er
    // valgfritt og brukes til filtrering i tillegg til/i stedet for label (f.eks.
    // produsent/opprinnelse). Vises IKKE i listen -- kun label vises. "group" (valgfritt)
    // grupperer listen med overskrifter -- søket går uansett på tvers av alle grupper,
    // grupperingen er kun visuell organisering av den allerede filtrerte listen.
    this.onSelect = onSelect;
    this.selectedId = null;
    this.highlightIndex = -1;
    this.filtered = [];
    this.instansId = `combobox-${++comboboxInstansTeller}`;

    const wrap = document.createElement("div");
    wrap.className = "combobox";

    const input = document.createElement("input");
    input.type = "text";
    input.className = "combobox-input";
    input.placeholder = placeholder;
    input.autocomplete = "off";
    input.spellcheck = false;
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-autocomplete", "list");
    if (ariaLabel) input.setAttribute("aria-label", ariaLabel);

    const list = document.createElement("ul");
    list.className = "combobox-list";
    list.id = `${this.instansId}-listbox`;
    list.hidden = true;
    list.setAttribute("role", "listbox");
    // Uten et autorisert tabindex-attributt gjør Chromium/Firefox denne
    // overflowende (max-height + overflow-y: auto) listen til et eget
    // Tab-stopp via "scrollable region"-heuristikken -- en uventet ekstra
    // stopp midt i combobox-mønsteret, der listen kun skal nås via piltaster
    // (se docs/development/web_combobox_tabindex_triage_184.md).
    list.setAttribute("tabindex", "-1");
    input.setAttribute("aria-controls", list.id);

    wrap.appendChild(input);
    wrap.appendChild(list);

    input.addEventListener("input", () => this._onInput());
    input.addEventListener("focus", () => this._onInput());
    input.addEventListener("keydown", (e) => this._onKeydown(e));
    input.addEventListener("blur", () => {
      // Kort delay slik at et "mousedown"/touch-valg av et alternativ
      // rekker å registreres før blur lukker listen.
      setTimeout(() => this._close(), 150);
    });

    this.el = wrap;
    this.inputEl = input;
    this.listEl = list;
  }

  _onInput() {
    const query = this.inputEl.value.trim().toLowerCase();
    this.filtered = query
      ? this.items.filter((it) => (it.search || it.label.toLowerCase()).includes(query))
      : this.items;
    this._renderList();
  }

  _renderList() {
    this.listEl.innerHTML = "";
    this.highlightIndex = -1;
    this.inputEl.removeAttribute("aria-activedescendant");
    if (this.filtered.length === 0) {
      this.listEl.hidden = true;
      this.inputEl.setAttribute("aria-expanded", "false");
      return;
    }
    let forrigeGruppe = undefined;
    let optionIndex = 0;
    for (const item of this.filtered) {
      if (item.group !== undefined && item.group !== forrigeGruppe) {
        const header = document.createElement("li");
        header.className = "combobox-gruppe-header";
        header.textContent = item.group;
        header.setAttribute("aria-hidden", "true");
        this.listEl.appendChild(header);
        forrigeGruppe = item.group;
      }
      const li = document.createElement("li");
      li.className = "combobox-option";
      li.id = `${this.instansId}-option-${optionIndex}`;
      li.textContent = item.label;
      li.setAttribute("role", "option");
      li.addEventListener("mousedown", (e) => {
        e.preventDefault(); // hindre blur før klikket rekker frem
        this._select(item);
      });
      this.listEl.appendChild(li);
      optionIndex++;
    }
    this.listEl.hidden = false;
    this.inputEl.setAttribute("aria-expanded", "true");
  }

  _onKeydown(e) {
    if (this.listEl.hidden) {
      if (e.key === "ArrowDown") this._onInput();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      this._move(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      this._move(-1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (this.highlightIndex >= 0) this._select(this.filtered[this.highlightIndex]);
    } else if (e.key === "Escape") {
      this._close();
    }
  }

  _move(delta) {
    const opts = [...this.listEl.querySelectorAll(".combobox-option")];
    if (opts.length === 0) return;
    if (this.highlightIndex >= 0) opts[this.highlightIndex].classList.remove("is-active");
    this.highlightIndex = (this.highlightIndex + delta + opts.length) % opts.length;
    const aktiv = opts[this.highlightIndex];
    aktiv.classList.add("is-active");
    aktiv.scrollIntoView({ block: "nearest" });
    this.inputEl.setAttribute("aria-activedescendant", aktiv.id);
  }

  _select(item) {
    this.selectedId = item.id;
    this.inputEl.value = item.label;
    this._close();
    this.onSelect(item.id, item);
  }

  _close() {
    this.listEl.hidden = true;
    this.inputEl.setAttribute("aria-expanded", "false");
    this.inputEl.removeAttribute("aria-activedescendant");
    this.highlightIndex = -1;
    const current = this.items.find((it) => it.id === this.selectedId);
    this.inputEl.value = current ? current.label : "";
    if (!current) this.selectedId = null;
  }

  getValue() {
    return this.selectedId;
  }

  setValue(id) {
    const item = this.items.find((it) => it.id === id);
    this.selectedId = item ? id : null;
    this.inputEl.value = item ? item.label : "";
  }

  clear() {
    this.selectedId = null;
    this.inputEl.value = "";
  }
}
