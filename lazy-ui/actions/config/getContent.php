<?php

include_once '../../includes/functions.php';

function getApproved() {
	include_once '../../includes/TVDB.php';
	global $db, $config;


	$html = '<form id="formID">';
	
	//TVDB Favs
	$tvdbusr = new TV_User();
	
	$xml = $tvdbusr->getFavs($config::$tvdbAccountID);
	
	if ($xml) {
		$html .= '<h3>TheTVDB.com Favorites</h3>';
		

		foreach($xml->Series as $show) {
			## Lets see if we can get the show info
			$sql = "SELECT * FROM tvdbcache where tvdbid = '$show'";
				
			$result = $db->prepare($sql);
			$result->execute();
	
			$tvdbRow = $result->fetch();

			$img = '';
			$title = '';
			
			if($tvdbRow) {
				$title = $tvdbRow['title'];
					
				if (array_key_exists('posterImg', $tvdbRow)) {
					if ($tvdbRow['posterImg'] != '') {
						$img = "<img src='images/downloaded/$show-tvdb.jpg'>";
					}
						
				}						
			} else {
				#Not found lets update it
				$tvshows = new TV_Shows();
				$tvshow = $tvshows->findById($show);
						
					if ($tvshow) {
						#Update DB
						$title = $tvshow->seriesName;
						$titleEsc = str_replace("'", "''", $title);
						
						if ($tvshow->poster != '') {
							//lets get it
							$imgSavePath = $config::$download_images;
							$posterurl = 'http://thetvdb.com/banners/_cache/' . $tvshow->poster;
							$imgFile = "$imgSavePath/$show-tvdb.jpg";
					
							file_put_contents($imgFile, file_get_contents($posterurl));
							chmod($imgFile, 0777);
							$img = "<img src='images/downloaded/$show-tvdb.jpg'>";
							
						}
	
						$sql = "INSERT into tvdbcache(title, tvdbid) values('$titleEsc', $show)";
						$db->exec($sql);
		
					} else {
						$title = "Unable to find show: $title";
					}
					

			}

			$html .= "
			<div class='download-item'>
			<div class='left-col'>
			<div style='float:left'><input role='checkbox' type='checkbox' class='item_$show' name='item[]' value='$show'></div>
			<div style='float:right'>$img</div>
			<div style='clear:both'></div>
			</div>
			<div class='right-col'>$title</div>
			</div>
			<div style='clear: both;'></div>";
		}
		
	}
	$approvedFile = $config::$approved_file;
	
	$titles = getTitleFromFile($approvedFile);

	if (is_array($titles)) {
		$html .= '<h3> Manual Auto Downloads</h3>';
		
		
		foreach($titles as $title) {
			$formattedTitle = str_replace('    - ', '', $title);
			$html .= "
			<div class='download-item'>
				<div class='left-col'>
					<div style='float:left'><input role='checkbox' type='checkbox' class='item_$show' name='item[]' value='$show'></div>
					<div style='clear:both'></div>
				</div>
				<div class='right-col'>$formattedTitle</div>
			</div>
			<div style='clear: both;'></div>";
		}
	}
	$html .= '</form>';
	echo $html;
	
}

function doManual() {
	$titles = getTitleFromFile('/home/media/.flexget/approve.yml');
	
	$html = '<h3>Manual Auto Downloads</h3>';
	$html .= '<form id="formID">';
	if (is_array($titles)) {
		foreach($titles as $title) {
			$formattedTitle = str_replace('    - ', '', $title);
			$html .= "
			<div class='download-item'>
				<div class='left-col'>
					<div style='float:left'><input role='checkbox' type='checkbox' class='item' name='manitem[]' value='$title'></div>
					<div style='clear:both'></div>
				</div>
				<div class='right-col'>$formattedTitle</div>
			</div>
			<div style='clear: both;'></div>";
		}
		}
		$html .= '</form>';
				echo $html;
}

function doTVDBAdd() {
	
	if (array_key_exists('search', $_GET) && $_GET['search'] != '') {
		include_once '../../includes/TVDB.php';
		echo "<form id='formID'>";
		$buttons = [
		['name' => 'Add Show', 'class' => 'button_addshow'],
		];
			
		$buttonsHTML = createButtons($buttons);
			
		$search = $_GET['search'];
		echo '<br><br><center><h3>Results for search: ' . $search . '</h3></center>';
		echo $buttonsHTML;
			
		$tvdbshows = new TV_Shows();
		
		$results = $tvdbshows->search($search);
		
		echo "<form id='formID'>";
		if (is_array($results)) {
			foreach ($results as $result) {
				$title = $result->seriesName;
				$id = $result->id;
					
				echo "
				<div class='download-item'>
				<div class='left-col'>
				<div style='float:left'><input role='checkbox' type='checkbox' class='item_$id' name='item[]' value='$id'></div>
				<div style='clear:both'></div>
				</div>
				<div class='right-col'>
				$title
				</div>
				</div>
				<div style='clear: both;'></div>";
			}
			}
				
			}
			echo "</form>";
			echo "</div>";
	
}


function addNewMapping() {

	if (array_key_exists('search', $_GET) && $_GET['search'] != '') {
	
		include_once '../../includes/TVDB.php';
		
		$buttons = [
		['name' => 'Add Mapping', 'class' => 'button_addshowmapping'],
		];
			
		$buttonsHTML = createButtons($buttons);
			
		$search = $_GET['search'];
		
		
		$tvdbshows = new TV_Shows();
		$smapTitle = htmlspecialchars($_GET['smapTitle'], ENT_QUOTES);

		$results = [];
		
		if (is_numeric($search)) {
			$tv_show = $tvdbshows->findById($search);
			if($tv_show instanceof TV_Show) {
				$results[] = $tv_show;
			}
		} else {
			$results = $tvdbshows->search($search);
		}
		if (count($results) == 0) {
			echo "<div class='left'><h3>No results found on thetvdb.com... try again</h3></div><div style='clear:both'></div>";
			echo "<div>Search for the TVDBShow below or enter thetvdb.com show id which corrosponds to the title</div>
			<form id='smapTitle' method='post' action='index.php?action=config&t=addnewmapping'>
			<input type='text' name='tvdbsearch' size='21' maxlength='120'>
			<input type='hidden' name='smapTitle' size='21' value='$smapTitle'>
			<input type='submit' value='Search TVDB'>
			</form>";
			return;
		}
	
		echo $buttonsHTML;		
		echo "<form id='formID'>";
		echo "<input type='hidden' name='smapTitle' value='$smapTitle'>";
		
		if (is_array($results)) {
			foreach ($results as $result) {
				$title = $result->seriesName;
				$id = $result->id;
				
					
				echo "
				<div class='download-item'>
				<div class='left-col'>
				<div style='float:left'><input role='checkbox' type='checkbox' class='item_$id' name='item' value='$id'></div>
				<div style='clear:both'></div>
				</div>
				<div class='right-col'>
				$title
				</div>
				</div>
				<div style='clear: both;'></div>";
			}
		}

	}
	echo "</form>";
	echo "</div>";

}



function doIgnore() {
	
	global $config;
	
	$html = '<h3>Ignore Downloads</h3>';
	
	echo "
			<form id='addignore' method='post' action='index.php?action=config&t=i'>
        		<input type='text' class='addignore' name='addignore' size='21' maxlength='120'><input type='submit' value='add' class='addignore'>
			</form>";
	
	if (array_key_exists('addignore', $_GET) && $_GET['addignore'] != '') {
		//Add to ignore
		$ignore = $_GET['addignore'];
		addToFile($ignore, '/home/media/.flexget/ignore.yml');
		echo "added to ignore";
	}
	
	$ignore_file = $config::$ignore_file;
	
	$titles = getTitleFromFile($ignore_file);
	
	$html .= '<form id="formID">';
	if (is_array($titles)) {
		foreach($titles as $title) {
			$formattedTitle = str_replace('    - ', '', $title);
			$html .= "
			<div class='download-item'>
			<div class='left-col'>
			<div style='float:left'><input role='checkbox' type='checkbox' class='item' name='manitemIgnore[]' value='$title'></div>
			<div style='clear:both'></div>
			</div>
			<div class='right-col'>$formattedTitle</div>
			</div>
			<div style='clear: both;'></div>";
		}
		}
		$html .= '</form>';
				echo $html;
}

function getShowMappings() {

	global $config;

	$html = '<div><h3>All shows with the title below are mapped to the corrosponding www.thetvdb.com show.</h3></div>
			<form id="formID">';
	
	$mapping = $config::$showMappings;

	foreach($mapping as $show => $tvdbID) {
		
		$html .= "
			<div class='download-item'>
				<div class='left-col'>
					<div style='float:left'><input role='checkbox' type='checkbox' class='item_$tvdbID' name='item[]' value='$show'></div>
					<div style='float:right'><img src='images/downloaded/$tvdbID-tvdb.jpg'></div>
					<div style='clear:both'></div>
				</div>
				<div class='right-col'>Title: $show</div>
				<div class='right-col smalltxt'>Mapped Show: <a href='http://thetvdb.com/?tab=series&id=$tvdbID'>http://thetvdb.com/?tab=series&id=$tvdbID</a></div>
			</div>";
	}
	
	$html .= "</form>";
	echo $html;
}

if (array_key_exists('t', $_GET)){
	if ($_GET['t'] == "a") {
		getApproved();
	} else if ($_GET['t'] == "tvdbaddnew") {
		doTVDBAdd();
	} else if ($_GET['t'] == "manual") {
		doManual();
	} else if ($_GET['t'] == "i") {
		doIgnore();
	} else if ($_GET['t'] == "a") {
		$this->doArchive();
	} else if ($_GET['t'] == "showmappings") {
		getShowMappings();
	} else if ($_GET['t'] == "addnewmapping") {
		addNewMapping();
	} else {
		return;
	}
}
	
?>
