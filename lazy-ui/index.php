<?php

include_once 'includes/functions.php';

if (isset($_GET["action"])) {

  $action = $_GET["action"];

  include_once "actions/$action/$action.php";

} else {
	include_once "actions/home/home.php";
}

$aClass = new action();

?>
<html>
<head>
	<link rel="stylesheet" type="text/css" href="style.css">
	<script src="jquery.js"></script>
	<script src="jquery-ui.js"></script>
	<link rel="stylesheet" href="jquery-ui-1.10.3.custom.css"/>
	<script src="lazy.js"></script>
	<?php $aClass->getHeader() ?>
</head>

<body>
	<div id="head-panel">
		<h1>Steve's Media Manager</h1>
		<div id="head-menu">
			<ul>
				<li><a href="index.php?action=home" title="">Home</a></li>
				<li><a href="index.php?action=downloads" title="">Downloads</a></li>
				<li><a href="index.php?action=other" title="">Other</a></li>
				<li><a href="index.php?action=config" title="">Config</a></li>
			</ul>
		</div>
		<div style="clear: both;"></div>
		<?php $aClass->getSubMenu() ?>
	</div>
	
	<br><br>
	<div id="body-wrapper" class="dokuwiki">
			
		
		<div id="content" lang="en" dir="ltr">
			<div id="loading" style='display:none'>
				<div id="floatingBarsG">
					<div class="blockG" id="rotateG_01"></div>
					<div class="blockG" id="rotateG_02"></div>
					<div class="blockG" id="rotateG_03"></div>
					<div class="blockG" id="rotateG_04"></div>
					<div class="blockG" id="rotateG_05"></div>
					<div class="blockG" id="rotateG_06"></div>
					<div class="blockG" id="rotateG_07"></div>
					<div class="blockG" id="rotateG_08"></div>
				</div>
				Loading...
			</div>
			<?php $aClass->getBody()?>
		</div>
	</div>
</body>
</html>