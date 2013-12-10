<?php


class action implements actionInterface {
	
	function getGeneral() {
		print yaml_parse_file('/home/media/.flexget/ignore.xml');
	}
	
	function doApproved() {
		
		$buttons = [
		['name' => 'Delete', 'class' => 'button_delete'],
		['name' => 'Add New', 'class' => 'button_page_addnew'],
		['name' => 'Add Manual', 'class' => 'button_page_manual'],
		];
		
		$buttonsHTML = createButtons($buttons);
			
		echo "<h2>Automatic Downloads</h2>";
		echo $buttonsHTML;
		echo "<div class='downloads' getType='a' action='config'></div>";
		echo $buttonsHTML;		
		
	}
	
	function doAddNew() {
		
		echo "<h2>Search for Shows</h2>";
		
		echo "
				<form id='tvdbsearch' method='post' action='/index.php?action=config&t=addnew'>
	        		<input type='text' class='tvdbsearch' name='tvdbsearch' size='21' maxlength='120'><input type='submit' value='search' class='tvdbsearch'>
				</form>";
		
		if (array_key_exists('tvdbsearch', $_POST) && $_POST['tvdbsearch'] != '') {
			$search = $_POST['tvdbsearch'];
			echo "<div class='downloads' getType='tvdbaddnew' action='config' post='&search=$search'></div>";
		} else {
			echo "<div class='downloads' getType='tvdbaddnew' action='config'></div>";
		}

	}
	
	function doAddMapping() {
	
		$html = "<h2>Manually map shows to a www.thetvdb.com show</h2>";
		
		if (array_key_exists('tvdbsearch', $_POST)) {
			$title = htmlspecialchars($_POST['smapTitle'], ENT_QUOTES);
			$search = $_POST['tvdbsearch'];
			
			$html .= "<div class='left'><h3>Select the correct show below that corrosponds to any shows with the title: $title</h3></div><div style='clear:both'></div>";
			
			$html .= "<div class='downloads' getType='addnewmapping' action='config' refresh='false' okPage='/index.php?action=config&t=smap' post='&smapTitle=$title&search=$search'></div>";
			
		} else if (array_key_exists('smapTitle', $_POST)) {
			$title = htmlspecialchars($_POST['smapTitle'], ENT_QUOTES);
						
			$html .= "<div class='left'><h3>Mapping show $title</h3></div><div style='clear:both'></div>
					  <div>Search for the TVDBShow below or enter thetvdb.com show id which corrosponds to the title</div>
				<form id='smapTitle' method='post' action='/index.php?action=config&t=addnewmapping'>
					<input type='text' name='tvdbsearch' size='21' maxlength='120'>
					<input type='hidden' name='smapTitle' size='21' maxlength='120' value='$title'>
					<input type='submit' value='Search TVDB'>
				</form>";
		} else {
			$html .= "<div class='left'><h3>Enter the title you want to map</h3></div>
					<div style='clear:both'></div>
					<div>
						<form id='smapTitle' method='post' action='/index.php?action=config&t=addnewmapping'>
	        			<input type='text' name='smapTitle' size='21' maxlength='120'><input type='submit' value='Submit Title' class='smapTitle'>
						</form>
					</div>";
		}
		
		echo $html;	
	}
	
	function doIgnore() {
		$buttons = [
		['name' => 'Delete', 'class' => 'button_delete'],
		];

		$buttonsHTML = createButtons($buttons);
			
		echo "<h2>Automatic Ignore</h2>";
		echo $buttonsHTML;

		if (array_key_exists('addignore', $_POST) && $_POST['addignore'] != '') {
			$ignore = $_POST['addignore'];
			echo "<div class='downloads' getType='i' action='config' post='&addignore=$ignore'></div>";
		} else {
			echo "<div class='downloads' getType='i' action='config'></div>";
		}
		
	
		echo $buttonsHTML;
	}

	function doManual() {

		$buttons = [
		['name' => 'Delete', 'class' => 'button_delete'],
		];
		$buttonsHTML = createButtons($buttons);
		
		echo "<h2>Add show manually</h2>";
		
		echo "
				<form id='manualshow' method='post' action='/index.php?action=config&t=manual'>
	        		<input type='text' class='manualshow' name='manualshow' size='21' maxlength='120'><input type='submit' value='add' class='manualshow'>
				</form>";
		
		if (array_key_exists('manualshow', $_POST) && $_POST['manualshow'] != '') {
			//add new show
			addToFileNoFormat($_POST['manualshow'], '/home/media/.flexget/approve.yml');
			echo 'Adding ' . $_POST['manualshow'] . ' Success';
		}
		echo $buttonsHTML;
		echo "<div class='downloads' getType='manual' action='config'></div>";
		
		
	}
	
	function doGeneral() {
		
		require_once 'Config/Lite.php';
		
		$config = new Config_Lite('/home/media/.lazy/config.cfg');
		
		$html .= "";
		
		foreach($config as $cfgSection => $section) {
			$html .= "<h1>$cfgSection</h1>";
			
			foreach ($section as $item) {
				$html .= "<div>$item</div>";
			}
		}
		
		echo $html;
		
	}
	
	function doShowMappings() {	
			
		$buttons = [
		['name' => 'Add New Mapping', 'class' => 'button_page_addnewmapping'],
		['name' => 'Delete', 'class' => 'button_deletemapping'],
		];
		$buttonsHTML = createButtons($buttons);
				
		
		echo $buttonsHTML;
		echo "<div class='downloads' getType='showmappings' action='config'></div>";
		
	}
	
	function getBody() {
		if (array_key_exists('t', $_GET)){
			if ($_GET['t'] == "a") {
				$this->doApproved();
			} else if ($_GET['t'] == "addnew") {
				$this->doAddNew();
			} else if ($_GET['t'] == "manual") {
				$this->doManual();
			} else if ($_GET['t'] == "i") {
				$this->doIgnore();	
			} else if ($_GET['t'] == "g"){
				$this->doGeneral();
			} else if ($_GET['t'] == "smap"){
				$this->doShowMappings();
			} else if ($_GET['t'] == "addnewmapping"){
					$this->doAddMapping();
			} else {
				$this->doApproved();
			}
		}
	}
	
	function getSubMenu() {
			echo '
				<ul id="page-actions2">
					<li><a href="/index.php?action=config&t=g">General</a></li>
					<li><a href="/index.php?action=config&t=a">Approved Shows</a></li>
					<li><a href="/index.php?action=config&t=i">Ignore Shows</a></li>
					<li><a href="/index.php?action=config&t=smap">Manual Show Mapping</a></li>
				</ul>';
	}
	
	function getHeader() {
		echo '<link rel="stylesheet" href="/actions/config/style.css"/>';
		
	}
	
}

?>