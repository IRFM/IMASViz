/*
 * Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
 * and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
 * CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
 * The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.
 *
 * Authors L. Fleury, X. Li, D. Penko
 *
 * -----------------------------------------------------------------------------
 * Which of the two themes of imasviz.css a page is read with.
 *
 * Three rules, in the order they are asked:
 *
 *   1. what this browser was last told (localStorage) -- a reader who picked
 *      dark should not have to pick it again on every page of the manual;
 *   2. what the reader's machine asks for (prefers-color-scheme);
 *   3. light.
 *
 * The theme is put on the document before the first paint -- this file is loaded
 * from the head, and setting the attribute is the first thing it does -- because
 * a page that arrives light and turns dark one frame later is worse than one
 * that was dark all along. The control is drawn afterwards, once the navigation
 * column exists.
 *
 * Nothing is fetched: no font, no script, no stylesheet from a network.
 * -----------------------------------------------------------------------------
 */

(function () {
  'use strict';

  var KEY = 'imasviz-theme';
  var LIGHT = 'light';
  var DARK = 'dark';

  function stored() {
    try {
      var value = window.localStorage.getItem(KEY);
      return (value === LIGHT || value === DARK) ? value : null;
    } catch (e) {
      /* A private mode that refuses storage is not a reason to lose the theme:
         the page still answers the machine's own preference. */
      return null;
    }
  }

  function remember(name) {
    try {
      window.localStorage.setItem(KEY, name);
    } catch (e) {
      /* Kept for this page only. */
    }
  }

  function askedByTheMachine() {
    return (window.matchMedia &&
            window.matchMedia('(prefers-color-scheme: ' + DARK + ')').matches)
        ? DARK : LIGHT;
  }

  function current() {
    return document.documentElement.getAttribute('data-theme') ||
           stored() || askedByTheMachine();
  }

  function apply(name) {
    document.documentElement.setAttribute('data-theme', name);
    return name;
  }

  apply(stored() || askedByTheMachine());

  function label(control, name) {
    var other = (name === DARK) ? LIGHT : DARK;
    control.textContent = other + ' theme';
    control.setAttribute('aria-label', 'Switch to the ' + other + ' theme');
    control.setAttribute('title',
                         'Currently the ' + name + ' theme');
  }

  function place() {
    if (document.getElementById('imasviz-theme-toggle')) {
      return;
    }
    var control = document.createElement('button');
    control.type = 'button';
    control.id = 'imasviz-theme-toggle';
    label(control, current());
    control.addEventListener('click', function () {
      var next = (current() === DARK) ? LIGHT : DARK;
      remember(apply(next));
      label(control, next);
    });

    var sidebar = document.querySelector('div.sphinxsidebarwrapper');
    if (sidebar) {
      sidebar.insertBefore(control, sidebar.firstChild);
    } else {
      var bar = document.querySelector('div.related ul');
      if (bar) {
        var slot = document.createElement('li');
        slot.appendChild(control);
        bar.appendChild(slot);
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', place);
  } else {
    place();
  }
})();
