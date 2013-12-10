<?php


class action implements actionInterface {
	
	function getXbmcLatestWatched() {
		
		$html = '';
		
		global $xbmcdb;
		
		
		$sql = "SELECT * FROM files ORDER BY lastPlayed DESC limit 30";
		
		foreach ($xbmcdb->query($sql) as $row) {
			
			$file = $row['strFilename'];
			$count = $row['playCount'];
			$lastPlayed = $row['lastPlayed'];
			$idPath = $row['idPath'];
			$path = '';
			
			if ($file == '') {
				continue;
			}
	
			$sql = "select strPath from path where idPath = $idPath";
			
			$result = $xbmcdb->prepare($sql);
			$result->execute();
		
			$pathRow = $result->fetch();
			
			if (is_array($pathRow) && array_key_exists('strPath', $pathRow)) {
				$strPath = $pathRow['strPath'];
				$path = "$strPath/$file";
			} else {
				$path = $file;
			}
			
			$html .= "
					<div class='xbmc-item'>
					File: $path
					<br>
					Count: $count
					<bR>
					When: $lastPlayed
					</div>";
		}
		
		echo $html;
		
		
		
		
	}
	
	function getJobs() {
		global $db;
		
		$buttons = [
		['name' => 'Delete Selected', 'class' => 'button_rpdelete'],
		['name' => 'Delete Old Reports', 'class' => 'button_rpdeleteold'],
		['name' => 'Delete ALL', 'class' => 'button_rpdeleteall'],
		];
		
		$buttonsHTML = createButtons($buttons);
			
		$html = "<h1>Jobs</h1>";
		$html .= $buttonsHTML;
		$html .= "<div class='downloads' getType='jobs' action='other'></div>";
		$html .= $buttonsHTML;
		
		echo $html;
		
	}
	
	function find() {		
		$html = '<h1>Find Movie or TVShow</h1>';
		
		
		$html .= "
			<form id='search' method='post' action='/index.php?action=other&t=find'>
        		<input type='text' name='search' size='21' maxlength='120'><input type='submit' value='Search'>
			</form>";
		
		if (array_key_exists('search', $_POST) && $_POST['search'] != '') {
			$search = $_POST['search'];
			$html .= "<div class='downloads' refresh='false' getType='find' action='other' post='&search=$search'></div>";
		} 
		
		echo $html;
	}
	
	function getMissing() {
				
		global $config;
		
		$buttons = [
		['name' => 'Report ALL Shows Missing', 'class' => 'button_rpallmissing'],
		['name' => 'Find and Fix ALL Shows', 'class' => 'button_autofix'],
		];
		
		$buttonsHTML = createButtons($buttons);
		
		$html = $buttonsHTML;
		$html .= '<h2>Fix Indvidual TV Show</h2>';
		
		//Get all tvshows
		$tvPath = $config::$tvshowsPath;
		$dirs = array_filter(glob("$tvPath/*"), 'is_dir');

		$showOptions = '';
		
		$search = '';
		if (array_key_exists('getmissingShow', $_POST) && $_POST['getmissingShow'] != '') {
			$search = $_POST['getmissingShow']; 
		}
		
		foreach($dirs as $dir) {
			$split = explode('/', $dir);
			
			$folder = $split[count($split) - 1];

			$folderESC = htmlspecialchars($folder, ENT_QUOTES);
			
			$selected = '';
			if ($search == $folder) {
				$selected = "selected";
			}
			
			$showOptions .= "<option value='$folderESC' $selected>$folder</option>";			
		}
		
		#First lets get all the shows in TVShows folder
		$html .= "
			<form method='post' action='/index.php?action=other&t=getmissing'>
				<select name='getmissingShow'>
					<option>Select TV Show</option>
					$showOptions	
				</select>
				<input type='submit' name='submit'>
			</form>";
		
		if (array_key_exists('getmissingShow', $_POST) && $_POST['getmissingShow'] != '') {
			$search = $_POST['getmissingShow'];
			$searchESC = htmlspecialchars($search, ENT_QUOTES);
			
			
			if (array_key_exists('showID', $_POST) && $_POST['showID'] != '') {
				$showID = $_POST['showID'];
				$searchESC .= "&showID=$showID";
			}
			
			//Lets find all the missing eps etc.
			$html .= "<div class='downloads' getType='getmissing' refresh='false' action='other' post='&search=$searchESC'></div>";
		}
		
		echo $html;
		
	}
	
	function getReport() {
		$id = $_GET['id'];
		echo "<div class='downloads' getType='getreport' action='other' post='&reportid=$id'></div>";
	}
	
	function cleanTV() {

		$buttons = [
		['name' => 'Delete Selected', 'class' => 'button_tvshowdelete'],
		];
		
		$buttonsHTML = createButtons($buttons);
			
		$html = "<h1>CleanUP TV</h1>";
		$html .= $buttonsHTML;
		$html .= "<div class='downloads' getType='cleantv' action='other'></div>";
		$html .= $buttonsHTML;
		
		echo $html;
	}

	function getBody() {
		if (array_key_exists('t', $_GET)){
			if ($_GET['t'] == "xbmcwatched") {
				$this->getXbmcLatestWatched();
			} else if ($_GET['t'] == "getreport") {
				$this->getReport();
			} else if ($_GET['t'] == "jobs") {
				$this->getJobs();
			} else if ($_GET['t'] == "getmissing") {
				$this->getMissing();
			} else if ($_GET['t'] == "find") {
				$this->find();
			} else if ($_GET['t'] == "cleantv") {
				$this->cleanTV();
			}
		} else {
			$this->getJobs();
		}
			
	
	}
	
	function getSubMenu() {
		echo '
				<ul id="page-actions2">
					<li><a href="/index.php?action=other&t=jobs">Jobs</a></li>
					<li><a href="/index.php?action=other&t=getmissing">Find Missing TV</a></li>
					<li><a href="/index.php?action=other&t=find">Manual Download</a></li>
					<li><a href="/index.php?action=other&t=find">Manaul Find TV/Movie</a></li>
				</ul>';
	}
	
	function getHeader() {
		echo '
					<script src="/actions/other/other.js"></script>
					<link rel="stylesheet" type="text/css" href="/actions/other/style.css">';
	}
	
}



?>