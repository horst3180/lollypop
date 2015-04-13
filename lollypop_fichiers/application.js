$(function() {

  $.ajax({
    url: '//github-windows.s3.amazonaws.com/changelog.jsonp',
    dataType: 'jsonp'
  })

  $animateIn = $(".animate-in");
  var animateInOffset = 100;

  // Only animate in elements if the browser supports animations
  if (browserSupportsCSSProperty('animation') && browserSupportsCSSProperty('transition')) {
    $animateIn.addClass("pre-animate");
  }

  $(window).scroll(function(e) {
    var windowHeight = $(window).height(),
      windowScrollPosition = $(window).scrollTop(),
      bottomScrollPosition = windowHeight + windowScrollPosition;

    $animateIn.each(function(i, element) {
      if ($(element).offset().top + animateInOffset < bottomScrollPosition) {
        $(element).removeClass('pre-animate');
      }
    });
  });

  if (isUsingUnsupportedOS()) {
    $('body').addClass('unsupported-os');
  }
})

// Called from changelog.jsonp
function JsonParse(data) {
  buildReleaseNotesFromData(data);
}

function buildReleaseNotesFromData(data) {
  var releases = $("<ul class='releases'/>")
    .append($.map(data.releases, createRelease));

  $("#changelog").empty().append(releases);
}

function createRelease(r) {
  return $("<li/>")
      .append($("<div class='release-header'/>")
        .append($("<span class='release-version'/>").text(r.version))
        .append($("<span class='release-name'/>").text(r.name ? r.name : r.description))
        .append($("<span class='release-date'/>").text(r.date ? r.date : "")))
      .append($("<ul class='changes'/>")
      .append($.map(r.changes, createChange)));
}

function createChange(changeText) {
  var m = changeText.match(/^(fixed|improved|removed|added)\s*:\s*(.*)/i);

  if (m) {
    return $("<li/>")
      .append($("<div class='change-label-container'/>")
        .append($("<em/>").addClass('change-label change-' + m[1].toLowerCase()).text(m[1])))
      .append(document.createTextNode(m[2]));
  }

  return $("<li/>").text(changeText);
}

function isUsingUnsupportedOS() {
  // Windows XP is not supported
  var userAgent = window.navigator.userAgent;
  return userAgent.indexOf('Windows NT 5.1') > -1 ||
    userAgent.indexOf('Windows NT 5.2') > -1;
}

function browserSupportsCSSProperty(propertyName) {
  var elm = document.createElement('div');
  propertyName = propertyName.toLowerCase();

  if (elm.style[propertyName] != undefined)
    return true;

  var propertyNameCapital = propertyName.charAt(0).toUpperCase() + propertyName.substr(1),
    domPrefixes = 'Webkit Moz ms O'.split(' ');

  for (var i = 0; i < domPrefixes.length; i++) {
    if (elm.style[domPrefixes[i] + propertyNameCapital] != undefined)
      return true;
  }

  return false;
}
