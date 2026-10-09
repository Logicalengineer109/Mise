// Row filter, column sorting, and the Leaflet map of loaded businesses.
(function () {
  var table = document.getElementById('rows');

  var filter = document.getElementById('filter');
  if (filter && table) {
    filter.addEventListener('input', function () {
      var needle = filter.value.toLowerCase();
      Array.prototype.forEach.call(table.tBodies[0].rows, function (row) {
        row.style.display = row.textContent.toLowerCase().indexOf(needle) === -1 ? 'none' : '';
      });
    });
  }

  if (table) {
    Array.prototype.forEach.call(table.tHead.rows[0].cells, function (th, index) {
      th.addEventListener('click', function () {
        var numeric = th.dataset.type === 'number';
        var ascending = !th.classList.contains('sorted-asc');
        var rows = Array.prototype.slice.call(table.tBodies[0].rows);

        rows.sort(function (a, b) {
          var x = a.cells[index].textContent.trim();
          var y = b.cells[index].textContent.trim();
          if (numeric) {
            x = parseFloat(x.replace(/,/g, '')) || 0;
            y = parseFloat(y.replace(/,/g, '')) || 0;
            return ascending ? x - y : y - x;
          }
          return ascending ? x.localeCompare(y) : y.localeCompare(x);
        });

        rows.forEach(function (row) { table.tBodies[0].appendChild(row); });
        Array.prototype.forEach.call(table.tHead.rows[0].cells, function (cell) {
          cell.classList.remove('sorted-asc', 'sorted-desc');
        });
        th.classList.add(ascending ? 'sorted-asc' : 'sorted-desc');
      });
    });
  }

  var mapEl = document.getElementById('map');
  if (mapEl && window.L) {
    fetch('/api/businesses')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var located = data.businesses.filter(function (b) { return b.latitude && b.longitude; });
        if (!located.length) { return; }

        var map = L.map('map');
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
          attribution: '&copy; OpenStreetMap, &copy; CARTO',
          maxZoom: 19
        }).addTo(map);

        var bounds = [];
        located.forEach(function (b) {
          bounds.push([b.latitude, b.longitude]);
          L.circleMarker([b.latitude, b.longitude], {
            radius: 7, color: '#d32323', weight: 2, fillColor: '#d32323', fillOpacity: 0.55
          }).addTo(map).bindPopup(
            '<b>' + b.business_name + '</b><br>' +
            (b.rating !== null ? b.rating + '★ ' : '') +
            (b.review_count || 0) + ' reviews' + (b.price ? ' &middot; ' + b.price : '') +
            '<br>' + (b.location || '')
          );
        });
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 14 });
      })
      .catch(function () { mapEl.style.display = 'none'; });
  }
})();
