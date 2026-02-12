<?php
/**
 * Router for PHP's built-in development server.
 * Handles MediaWiki short URLs (/wiki/Article_Name).
 *
 * Usage: php -S localhost:8080 -t wiki wiki/router.php
 */

$url = parse_url( $_SERVER['REQUEST_URI'] );
$path = $url['path'] ?? '/';

// Serve existing static files directly (CSS, JS, images)
$filePath = __DIR__ . $path;
if ( $path !== '/' && is_file( $filePath ) ) {
	return false;
}

// /wiki/Article_Name -> index.php?title=Article_Name
if ( preg_match( '#^/wiki/(.*)$#', $path, $matches ) ) {
	$_GET['title'] = urldecode( $matches[1] );
	require __DIR__ . '/index.php';
	return true;
}

// /wiki with no article -> Main Page
if ( $path === '/wiki' || $path === '/wiki/' ) {
	$_GET['title'] = 'Main_Page';
	require __DIR__ . '/index.php';
	return true;
}

// Bare / -> Main Page
if ( $path === '/' ) {
	$_GET['title'] = 'Main_Page';
	require __DIR__ . '/index.php';
	return true;
}

// Other .php scripts (api.php, load.php, etc.)
$scriptFile = __DIR__ . $path;
if ( is_file( $scriptFile ) && pathinfo( $scriptFile, PATHINFO_EXTENSION ) === 'php' ) {
	require $scriptFile;
	return true;
}

// Fallback
require __DIR__ . '/index.php';
return true;
