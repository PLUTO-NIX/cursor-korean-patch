(function(){
  var _dict = '${RUNTIME_DICT}';
  if (!_dict || _dict === '${' + 'RUNTIME_DICT}') return;

  var SETTINGS_SELECTORS = [
    '.cursor-settings-layout-main',
    '.settings-editor',
    '.cursor-settings-container',
    '.monaco-dialog-box'
  ];
  var _applied = new WeakSet();

  function matchEntry(txt, entry) {
    if (entry.type === 'exact') {
      return txt.trim() === entry.en;
    } else if (entry.type === 'partial') {
      return txt.indexOf(entry.en) !== -1;
    } else if (entry.type === 'regex') {
      var re = new RegExp(entry.en, entry.flags || 'g');
      return re.test(txt);
    }
    return false;
  }

  function applyEntry(txt, entry) {
    if (entry.type === 'exact') {
      return entry.ko;
    } else if (entry.type === 'partial') {
      return txt.replace(entry.en, entry.ko);
    } else if (entry.type === 'regex') {
      return txt.replace(new RegExp(entry.en, entry.flags || 'g'), entry.ko);
    }
    return txt;
  }

  function translateTextNodes(root) {
    if (!root) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function(n) {
        if (_applied.has(n)) return NodeFilter.FILTER_REJECT;
        return n.textContent && n.textContent.trim().length > 0
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_REJECT;
      }
    });
    var node;
    while (node = walker.nextNode()) {
      var txt = node.textContent;
      var changed = false;
      for (var i = 0; i < _dict.length; i++) {
        if (matchEntry(txt, _dict[i])) {
          txt = applyEntry(txt, _dict[i]);
          changed = true;
        }
      }
      if (changed) {
        node.textContent = txt;
        _applied.add(node);
      }
    }
  }

  function translateAttributes(root) {
    if (!root) return;
    var els = root.querySelectorAll('[placeholder], [aria-label], [title]');
    for (var j = 0; j < els.length; j++) {
      var el = els[j];
      ['placeholder', 'aria-label', 'title'].forEach(function(attr) {
        var val = el.getAttribute(attr);
        if (!val) return;
        for (var i = 0; i < _dict.length; i++) {
          if (matchEntry(val, _dict[i])) {
            el.setAttribute(attr, applyEntry(val, _dict[i]));
            break;
          }
        }
      });
    }
  }

  function translateSelectOptions(root) {
    if (!root) return;
    var selects = root.querySelectorAll('select');
    for (var s = 0; s < selects.length; s++) {
      var opts = selects[s].querySelectorAll('option');
      for (var o = 0; o < opts.length; o++) {
        var txt = opts[o].textContent;
        for (var i = 0; i < _dict.length; i++) {
          if (matchEntry(txt, _dict[i])) {
            opts[o].textContent = applyEntry(txt, _dict[i]);
            break;
          }
        }
      }
    }
  }

  function translateAll(root) {
    translateTextNodes(root);
    translateAttributes(root);
    translateSelectOptions(root);
  }

  function init() {
    var found = false;
    for (var s = 0; s < SETTINGS_SELECTORS.length; s++) {
      var targets = document.querySelectorAll(SETTINGS_SELECTORS[s]);
      for (var t = 0; t < targets.length; t++) {
        found = true;
        var el = targets[t];
        translateAll(el);
        if (!el.__koObserver) {
          el.__koObserver = new MutationObserver(function(mutations) {
            for (var m = 0; m < mutations.length; m++) {
              var mut = mutations[m];
              if (mut.type === 'childList') {
                for (var a = 0; a < mut.addedNodes.length; a++) {
                  var added = mut.addedNodes[a];
                  if (added.nodeType === 1) translateAll(added);
                  else if (added.nodeType === 3 && !_applied.has(added)) {
                    var txt = added.textContent;
                    for (var i = 0; i < _dict.length; i++) {
                      if (matchEntry(txt, _dict[i])) {
                        added.textContent = applyEntry(txt, _dict[i]);
                        _applied.add(added);
                        break;
                      }
                    }
                  }
                }
              } else if (mut.type === 'characterData' && !_applied.has(mut.target)) {
                var cTxt = mut.target.textContent;
                for (var ci = 0; ci < _dict.length; ci++) {
                  if (matchEntry(cTxt, _dict[ci])) {
                    mut.target.textContent = applyEntry(cTxt, _dict[ci]);
                    _applied.add(mut.target);
                    break;
                  }
                }
              }
            }
          });
          el.__koObserver.observe(el, { childList: true, subtree: true, characterData: true });
        }
      }
    }
    return found;
  }

  var _initObserver = new MutationObserver(function() {
    for (var s = 0; s < SETTINGS_SELECTORS.length; s++) {
      if (document.querySelector(SETTINGS_SELECTORS[s])) {
        init();
        return;
      }
    }
  });

  if (document.body) {
    _initObserver.observe(document.body, { childList: true, subtree: true });
  } else {
    document.addEventListener('DOMContentLoaded', function() {
      _initObserver.observe(document.body, { childList: true, subtree: true });
    });
  }

  for (var s = 0; s < SETTINGS_SELECTORS.length; s++) {
    if (document.querySelector(SETTINGS_SELECTORS[s])) {
      init();
      break;
    }
  }
})();
