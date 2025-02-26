const MAIN_BLOCK = "dual-listbox";

const CONTAINER_ELEMENT = "dual-listbox__container";
const AVAILABLE_ELEMENT = "dual-listbox__available";
const SELECTED_ELEMENT = "dual-listbox__selected";
const TITLE_ELEMENT = "dual-listbox__title";
const ITEM_ELEMENT = "dual-listbox__item";
const BUTTONS_ELEMENT = "dual-listbox__buttons";
const BUTTON_ELEMENT = "dual-listbox__button";
const SEARCH_ELEMENT = "dual-listbox__search";

const SELECTED_MODIFIER = "dual-listbox__item--selected";

const DIRECTION_UP = "up";
const DIRECTION_DOWN = "down";

/**
 * Dual select interface allowing the user to select items from a list of provided options.
 * @class
 */
class DualListbox {
    constructor(selector, options = {}) {
        this.setDefaults();
        this.dragged = null;
        this.options = [];
        this.selectedItems = new Set();
        this.lastSelected = null;
        this.searchTermLeft = '';  // Store left search term
        this.searchTermRight = ''; // Store right search term

        if (DualListbox.isDomElement(selector)) {
            this.select = selector;
        } else {
            this.select = document.querySelector(selector);
        }

        this._initOptions(options);
        this._initReusableElements();
        if (options.options !== undefined) {
            this.options = options.options;
        } else {
            this._splitOptions(this.select.options);
        }

        this._buildDualListbox(this.select.parentNode);
        this._addActions();

        if (this.showSortButtons) {
            this._initializeSortButtons();
        }

        this.redraw();
    }

    /**
     * Sets the default values that can be overwritten.
     */
    setDefaults() {
        this.availableTitle = "Available options";
        this.selectedTitle = "Selected options";

        this.showAddButton = true;
        this.addButtonText = "add";

        this.showRemoveButton = true;
        this.removeButtonText = "remove";

        this.showAddAllButton = true;
        this.addAllButtonText = "add all";

        this.showRemoveAllButton = true;
        this.removeAllButtonText = "remove all";

        this.searchPlaceholder = "Search";

        this.showSortButtons = false;
        this.sortFunction = (a, b) => 0;

        this.upButtonText = "up";
        this.downButtonText = "down";

        this.enableDoubleClick = true;
        this.draggable = true;
        this.multiSelect = true;
    }

    /**
     * Change the order of options in the list
     */
    changeOrder(items, newPosition) {
        if (!Array.isArray(items)) {
            items = [items];
        }

        // Sort items by their current index to maintain relative order
        const itemsWithIndices = items.map(item => ({
            item,
            index: this.options.findIndex(opt => opt.value === item.dataset.id)
        })).sort((a, b) => a.index - b.index);

        // Remove items from their current positions
        const removedItems = itemsWithIndices.map(({item, index}) =>
            this.options.splice(index, 1)[0]
        );

        // Insert items at the new position
        this.options.splice(newPosition, 0, ...removedItems);
    }

    /**
     * Add options to the dual listbox
     */
    addOptions(options) {
        options.forEach((option) => {
            this.addOption(option);
        });
    }

    /**
     * Add option to the dual listbox
     */
    addOption(option, index = null) {
        if (index !== null) {
            this.options.splice(index, 0, option);
        } else {
            this.options.push(option);
        }
    }

    /**
     * Add event listener to the dual listbox
     */
    addEventListener(eventName, callback) {
        this.dualListbox.addEventListener(eventName, callback);
    }

    /**
     * Toggle selection state of items
     */
    toggleSelection(listItem, event) {
        if (this.multiSelect && (event.ctrlKey || event.metaKey)) {
            // Toggle individual item
            if (this.selectedItems.has(listItem)) {
                this.selectedItems.delete(listItem);
                listItem.classList.remove(SELECTED_MODIFIER);
            } else {
                this.selectedItems.add(listItem);
                listItem.classList.add(SELECTED_MODIFIER);
            }
        } else if (this.multiSelect && event.shiftKey && this.lastSelected) {
            // Range selection
            const items = Array.from(listItem.parentElement.children);
            const currentIndex = items.indexOf(listItem);
            const lastIndex = items.indexOf(this.lastSelected);
            const [start, end] = [Math.min(currentIndex, lastIndex), Math.max(currentIndex, lastIndex)];

            // Clear previous selections
            this.selectedItems.clear();
            items.forEach(item => item.classList.remove(SELECTED_MODIFIER));

            // Select range
            for (let i = start; i <= end; i++) {
                this.selectedItems.add(items[i]);
                items[i].classList.add(SELECTED_MODIFIER);
            }
        } else {
            // Single selection
            this.selectedItems.clear();
            listItem.parentElement.querySelectorAll(`.${ITEM_ELEMENT}`).forEach(item => {
                item.classList.remove(SELECTED_MODIFIER);
            });
            this.selectedItems.add(listItem);
            listItem.classList.add(SELECTED_MODIFIER);
        }

        this.lastSelected = listItem;
    }

    /**
     * Change selected state of items
     */
    changeSelected(items) {
        if (!Array.isArray(items)) {
            items = [items];
        }

        // Filter out any null or undefined items
        items = items.filter(item => item != null);

        if (items.length === 0) {
            return; // Exit if no valid items to process
        }

        // Track whether we're selecting or deselecting before making changes
        const isSelecting = items[0].parentElement?.classList.contains(AVAILABLE_ELEMENT) ?? false;

        items.forEach(listItem => {
            const changeOption = this.options.find(
                (option) => option.value === listItem.dataset.id
            );
            if (changeOption) {
                changeOption.selected = !changeOption.selected;
            }
        });

        this.redraw();

        setTimeout(() => {
            let event = document.createEvent("HTMLEvents");
            // Use the tracked state to determine the event type
            event.initEvent(isSelecting ? "added" : "removed", false, true);
            event.affectedElements = items;
            this.dualListbox.dispatchEvent(event);
        }, 0);
    }

    /**
     * Get visible items from a list
     */
    _getVisibleItems(list) {
        return Array.from(list.querySelectorAll(`.${ITEM_ELEMENT}`))
            .filter(item => item.style.display !== 'none')
            .map(item => item.dataset.id);
    }

    /**
     * Select all visible items
     */
    actionAllSelected(event) {
        if (event) {
            event.preventDefault();
        }

        // Get only visible items from available list
        const visibleIds = this._getVisibleItems(this.availableList);

        // Update only visible items
        this.options.forEach((option) => {
            if (visibleIds.includes(option.value)) {
                option.selected = true;
            }
        });

        this.redraw();
    }

    /**
     * Deselect all visible items
     */
    actionAllDeselected(event) {
        if (event) {
            event.preventDefault();
        }

        // Get only visible items from selected list
        const visibleIds = this._getVisibleItems(this.selectedList);

        // Update only visible items
        this.options.forEach((option) => {
            if (visibleIds.includes(option.value)) {
                option.selected = false;
            }
        });

        this.redraw();
    }

    /**
     * Move selected items to selected list
     */
    actionItemSelected(event) {
        event.preventDefault();
        const selected = Array.from(this.selectedItems).filter(item =>
            item.parentElement.classList.contains(AVAILABLE_ELEMENT)
        );
        if (selected.length > 0) {
            this.changeSelected(selected);
        }
    }

    /**
     * Move selected items to available list
     */
    actionItemDeselected(event) {
        event.preventDefault();
        const selected = Array.from(this.selectedItems).filter(item =>
            item.parentElement.classList.contains(SELECTED_ELEMENT)
        );
        if (selected.length > 0) {
            this.changeSelected(selected);
        }
    }

    /**
     * Redraws the Dual listbox content
     */
    redraw() {
        this.updateAvailableListbox();
        this.updateSelectedListbox();
        this._reapplySearchFilters(); // Reapply search filters after redraw
        this.syncSelect();
    }

    /**
     * Search through the items in the dual listbox
     */
    searchLists(searchString, dualListbox) {
        let items = dualListbox.querySelectorAll(`.${ITEM_ELEMENT}`);
        let lowerCaseSearchString = searchString.toLowerCase();

        // Store search terms
        if (dualListbox === this.availableList) {
            this.searchTermLeft = searchString;
        } else if (dualListbox === this.selectedList) {
            this.searchTermRight = searchString;
        }

        this._applySearchFilter(items, lowerCaseSearchString);
    }

    /**
     * Apply search filter to items
     */
    _applySearchFilter(items, searchString) {
        for (let i = 0; i < items.length; i++) {
            let item = items[i];
            if (searchString && item.textContent.toLowerCase().indexOf(searchString) === -1) {
                item.style.display = "none";
            } else {
                item.style.display = "list-item";
            }
        }
    }

    /**
     * Reapply current search filters after redraw
     */
    _reapplySearchFilters() {
        if (this.searchTermLeft) {
            this._applySearchFilter(
                this.availableList.querySelectorAll(`.${ITEM_ELEMENT}`),
                this.searchTermLeft.toLowerCase()
            );
        }
        if (this.searchTermRight) {
            this._applySearchFilter(
                this.selectedList.querySelectorAll(`.${ITEM_ELEMENT}`),
                this.searchTermRight.toLowerCase()
            );
        }
    }

    /**
     * Update available listbox
     */
    updateAvailableListbox() {
        this._updateListbox(
            this.availableList,
            this.options.filter((option) => !option.selected)
        );
    }

    /**
     * Update selected listbox
     */
    updateSelectedListbox() {
        this._updateListbox(
            this.selectedList,
            this.options.filter((option) => option.selected)
        );
    }

    /**
     * Sync with original select element
     */
    syncSelect() {
        while (this.select.firstChild) {
            this.select.removeChild(this.select.lastChild);
        }

        this.options.forEach((option) => {
            let optionElement = document.createElement("option");
            optionElement.value = option.value;
            optionElement.innerText = option.text;
            if (option.selected) {
                optionElement.setAttribute("selected", "selected");
            }
            this.select.appendChild(optionElement);
        });
    }

    /**
     * Update listbox content
     */
    _updateListbox(list, options) {
        while (list.firstChild) {
            list.removeChild(list.firstChild);
        }

        options.forEach((option) => {
            list.appendChild(this._createListItem(option));
        });
    }

    /**
     * Add actions to the elements
     */
    _addActions() {
        this._addButtonActions();
        this._addSearchActions();
    }

    /**
     * Add button actions
     */
    _addButtonActions() {
        this.add_all_button.addEventListener("click", (event) =>
            this.actionAllSelected(event)
        );
        this.add_button.addEventListener("click", (event) =>
            this.actionItemSelected(event)
        );
        this.remove_button.addEventListener("click", (event) =>
            this.actionItemDeselected(event)
        );
        this.remove_all_button.addEventListener("click", (event) =>
            this.actionAllDeselected(event)
        );
    }

    /**
     * Add search actions
     */
    _addSearchActions() {
        this.search_left.addEventListener("input", (event) =>
            this.searchLists(event.target.value, this.availableList)
        );
        this.search_right.addEventListener("input", (event) =>
            this.searchLists(event.target.value, this.selectedList)
        );
    }

    /**
     * Add click actions to list items
     */
    _addClickActions(listItem) {
        listItem.addEventListener("dblclick", (event) => {
            if (this.enableDoubleClick) {
                event.preventDefault();
                event.stopPropagation();
                this.changeSelected([listItem]);
            }
        });

        listItem.addEventListener("click", (event) => {
            event.preventDefault();
            this.toggleSelection(listItem, event);
        });

        return listItem;
    }

    /**
     * Build the dual listbox structure
     */
    _buildDualListbox(container) {
        this.select.style.display = "none";

        const leftSearch = this._createSearchLeft();
        const rightSearch = this._createSearchRight();

        this.dualListBoxContainer.appendChild(
            this._createList(leftSearch, this.availableListTitle, this.availableList)
        );
        this.dualListBoxContainer.appendChild(this.buttons);
        this.dualListBoxContainer.appendChild(
            this._createList(rightSearch, this.selectedListTitle, this.selectedList)
        );

        this.dualListbox.appendChild(this.dualListBoxContainer);
        container.insertBefore(this.dualListbox, this.select);
    }

    /**
     * Create a list container with search and title
     */
    _createList(search, header, list) {
        let result = document.createElement("div");
        result.appendChild(search);
        result.appendChild(header);
        result.appendChild(list);
        return result;
    }

    /**
     * Create the buttons for moving items
     */
    _createButtons() {
        this.buttons = document.createElement("div");
        this.buttons.classList.add(BUTTONS_ELEMENT);

        this.add_all_button = document.createElement("button");
        this.add_all_button.innerHTML = this.addAllButtonText;

        this.add_button = document.createElement("button");
        this.add_button.innerHTML = this.addButtonText;

        this.remove_button = document.createElement("button");
        this.remove_button.innerHTML = this.removeButtonText;

        this.remove_all_button = document.createElement("button");
        this.remove_all_button.innerHTML = this.removeAllButtonText;

        const options = {
            showAddAllButton: this.add_all_button,
            showAddButton: this.add_button,
            showRemoveButton: this.remove_button,
            showRemoveAllButton: this.remove_all_button,
        };

        for (let optionName in options) {
            if (optionName) {
                const option = this[optionName];
                const button = options[optionName];

                button.setAttribute("type", "button");
                button.classList.add(BUTTON_ELEMENT);

                if (option) {
                    this.buttons.appendChild(button);
                }
            }
        }
    }

    /**
     * Create a list item
     */
    _createListItem(option) {
        let listItem = document.createElement("li");
        listItem.classList.add(ITEM_ELEMENT);
        listItem.innerHTML = option.text;
        listItem.dataset.id = option.value;

        this._liListeners(listItem);
        this._addClickActions(listItem);

        if (this.draggable) {
            listItem.setAttribute("draggable", "true");
        }

        return listItem;
    }

    /**
     * Add drag and drop listeners to list items
     */
    _liListeners(li) {
        li.addEventListener("dragstart", (event) => {
            this.dragged = event.currentTarget;
            event.currentTarget.classList.add("dragging");

            // If dragged item is not in selection, clear selection and select only dragged item
            if (!this.selectedItems.has(this.dragged)) {
                this.selectedItems.clear();
                this.toggleSelection(this.dragged, { ctrlKey: false });
            }
        });

        li.addEventListener("dragend", (event) => {
            event.currentTarget.classList.remove("dragging");
        });

        li.addEventListener("dragover", (event) => {
            event.preventDefault();
        });

        li.addEventListener("dragenter", (event) => {
            event.target.classList.add("drop-above");
        });

        li.addEventListener("dragleave", (event) => {
            event.target.classList.remove("drop-above");
        });

        li.addEventListener("drop", (event) => {
            event.preventDefault();
            event.stopPropagation();
            event.target.classList.remove("drop-above");

            const newIndex = this.options.findIndex(
                (option) => option.value === event.target.dataset.id
            );

            const selectedItems = Array.from(this.selectedItems);
            if (event.target.parentElement === this.dragged.parentElement) {
                this.changeOrder(selectedItems, newIndex);
            } else {
                this.changeSelected(selectedItems);
                this.changeOrder(selectedItems, newIndex);
            }

            this.redraw();
        });
    }

    /**
     * Create drag and drop listeners for the listboxes
     */
    _createDragListeners() {
        [this.availableList, this.selectedList].forEach((dropzone) => {
            dropzone.addEventListener("dragover", (event) => {
                event.preventDefault();
            }, false);

            dropzone.addEventListener("dragenter", (event) => {
                event.target.classList.add("drop-in");
            });

            dropzone.addEventListener("dragleave", (event) => {
                event.target.classList.remove("drop-in");
            });

            dropzone.addEventListener("drop", (event) => {
                event.preventDefault();
                event.target.classList.remove("drop-in");

                if (dropzone.classList.contains(SELECTED_ELEMENT) ||
                    dropzone.classList.contains(AVAILABLE_ELEMENT)) {
                    const selectedItems = Array.from(this.selectedItems);
                    this.changeSelected(selectedItems);
                }
            });
        });
    }

    /**
     * Create the search input for the left side
     */
    _createSearchWithReset(side) {
        const searchContainer = document.createElement("div");
        searchContainer.classList.add("dual-listbox__search-container");
        searchContainer.style.display = "flex";
        searchContainer.style.alignItems = "center";
        searchContainer.style.gap = "4px";

        const searchInput = document.createElement("input");
        searchInput.classList.add(SEARCH_ELEMENT);
        searchInput.placeholder = this.searchPlaceholder;
        searchInput.style.flex = "1";

        const resetButton = document.createElement("button");
        resetButton.type = "button";
        resetButton.classList.add("dual-listbox__search-reset");
        resetButton.innerHTML = "×"; // Using × symbol for clear
        resetButton.style.padding = "2px 6px";
        resetButton.style.border = "1px solid #ccc";
        resetButton.style.borderRadius = "3px";
        resetButton.style.cursor = "pointer";
        resetButton.style.backgroundColor = "#fff";
        resetButton.title = "Clear search";

        resetButton.addEventListener("click", () => {
            searchInput.value = "";
            if (side === "left") {
                this.searchTermLeft = "";
                this.searchLists("", this.availableList);
            } else {
                this.searchTermRight = "";
                this.searchLists("", this.selectedList);
            }
            searchInput.focus();
        });

        searchContainer.appendChild(searchInput);
        searchContainer.appendChild(resetButton);

        return {
            container: searchContainer,
            input: searchInput
        };
    }

    /**
     * Create the search input for the left side
     */
    _createSearchLeft() {
        const { container, input } = this._createSearchWithReset("left");
        this.search_left = input;
        return container;
    }

    /**
     * Create the search input for the right side
     */
    _createSearchRight() {
        const { container, input } = this._createSearchWithReset("right");
        this.search_right = input;
        return container;
    }

    /**
     * Initialize options from constructor
     */
    _initOptions(options) {
        for (let key in options) {
            if (options.hasOwnProperty(key)) {
                this[key] = options[key];
            }
        }
    }

    /**
     * Initialize reusable elements
     */
    _initReusableElements() {
        this.dualListbox = document.createElement("div");
        this.dualListbox.classList.add(MAIN_BLOCK);
        if (this.select.id) {
            this.dualListbox.classList.add(this.select.id);
        }

        this.dualListBoxContainer = document.createElement("div");
        this.dualListBoxContainer.classList.add(CONTAINER_ELEMENT);

        this.availableList = document.createElement("ul");
        this.availableList.classList.add(AVAILABLE_ELEMENT);

        this.selectedList = document.createElement("ul");
        this.selectedList.classList.add(SELECTED_ELEMENT);

        this.availableListTitle = document.createElement("div");
        this.availableListTitle.classList.add(TITLE_ELEMENT);
        this.availableListTitle.innerText = this.availableTitle;

        this.selectedListTitle = document.createElement("div");
        this.selectedListTitle.classList.add(TITLE_ELEMENT);
        this.selectedListTitle.innerText = this.selectedTitle;

        this._createButtons();
        this._createSearchLeft();
        this._createSearchRight();

        if (this.draggable) {
            setTimeout(() => {
                this._createDragListeners();
            }, 10);
        }
    }

    /**
     * Initialize sort buttons
     */
    _initializeSortButtons() {
        const sortUpButton = document.createElement("button");
        sortUpButton.classList.add(BUTTON_ELEMENT);
        sortUpButton.innerText = this.upButtonText;
        sortUpButton.addEventListener("click", (event) =>
            this._onSortButtonClick(event, DIRECTION_UP)
        );

        const sortDownButton = document.createElement("button");
        sortDownButton.classList.add(BUTTON_ELEMENT);
        sortDownButton.innerText = this.downButtonText;
        sortDownButton.addEventListener("click", (event) =>
            this._onSortButtonClick(event, DIRECTION_DOWN)
        );

        const buttonContainer = document.createElement("div");
        buttonContainer.classList.add(BUTTONS_ELEMENT);
        buttonContainer.appendChild(sortUpButton);
        buttonContainer.appendChild(sortDownButton);

        this.dualListBoxContainer.appendChild(buttonContainer);
    }

    /**
     * Handle sort button clicks
     */
    _onSortButtonClick(event, direction) {
        event.preventDefault();
        const selectedItems = Array.from(this.selectedItems);

        if (selectedItems.length > 0) {
            const indices = selectedItems.map(item =>
                this.options.findIndex(option => option.value === item.dataset.id)
            );

            const minIndex = Math.min(...indices);
            const maxIndex = Math.max(...indices);

            let newIndex = direction === DIRECTION_UP ?
                Math.max(0, minIndex - 1) :
                Math.min(this.options.length - selectedItems.length, maxIndex + 1);

            this.changeOrder(selectedItems, newIndex);
            this.redraw();
        }
    }

    /**
     * Split options from select element
     */
    _splitOptions(options) {
        [...options].forEach((option, index) => {
            this.addOption({
                text: option.innerHTML,
                value: option.value,
                selected: option.hasAttribute("selected"),
                order: index,
            });
        });
    }

    /**
     * Check if an object is a DOM element
     */
    static isDomElement(o) {
        return typeof HTMLElement === "object" ?
            o instanceof HTMLElement :
            o && typeof o === "object" && o !== null && o.nodeType === 1 && typeof o.nodeName === "string";
    }
}

window.DualListbox = DualListbox;