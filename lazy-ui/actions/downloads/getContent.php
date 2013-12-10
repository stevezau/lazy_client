<?php

include_once '../../includes/functions.php';
	

if ($_GET["t"] && ctype_digit($_GET["t"])) {
	
	$type = $_GET["t"];
	
	//Specials
	if ($type == "10") {
		doSpecials();
		return;
	}
	
	$sql = "SELECT count(*) FROM download WHERE status = $type";
	$result = $db->query($sql);
	
	$rowCount = $result->fetch(PDO::FETCH_NUM);
		
	$sql = "SELECT * FROM download where status = $type";
	
	if ($_GET['t'] == 3) {
		$sql = $sql . " AND message != ''";	
	}
	
	if ($_GET['t'] == 1) {
		$sql = $sql . " ORDER BY priority ASC, ID ";
	} else {
		$sql = $sql . " ORDER BY ID DESC ";
	}
	
	if ($_GET['t'] == 4) {
		$sql = $sql . " LIMIT 40 ";
	}
	$items = Array();
	
	foreach ($db->query($sql) as $row) {
		$title = $row['title'];
		
		
		if ($row['section' == "TVHD"] && $type == "6") {
			# Lets get the title first
			$title = $row['title'];
			
			preg_match('/(^.*)\.S[0-9][0-9]?/', $title, $matches);
			
			if (array_key_exists(1, $matches)) {
				//We have a title, first lets check if its already in the array
				if (array_key_exists($matches[1], $items)) {
					//append this one
					$items[$matches[1]][] = $row;
				} else {
					//lets add it then
					$items[$matches[1]]['hasOthers'] = true;
					$items[$matches[1]]['title'] = $matches[1];
					$items[$matches[1]][] = $row;
					
				}
				
			} else {
				//didnt find a match, add it as a normal item
				$items[$title][] = $row;
				$items[$title]['title'] = $title;
			}
					
		} else {
			$items[$title][] = $row;
			$items[$title]['title'] = $title;
		}
	
	}
	
	echo '<form id="formID">';
	echo "<div class='middle pad10'>Total $rowCount[0]</div>";
	foreach ($items as $item) {
		buildDiv($item);
	}
	echo '</form>';
}

function getPercentComplete($localpath, $remoteSize) {

	$localpath = trim($localpath);
	
	$percentComplete = 0;
		
	if (file_exists($localpath)) {
		$localsize = getDirSize($localpath);
		$remotesize = round($remoteSize / 1048576, 2);
				
		if ($localsize > 0 ) {
			$percentComplete = round($localsize / $remotesize * 100, 2);
		}
			
	}
	return $percentComplete;
}

	
function buildDiv($array) {

	global $db;
	
	//how many releaes we working with here?
	$items = Array();
	
	foreach ($array as $item) {
		if (is_array($item)) {
			$items[] = $item;
		}
	}
	
	$count = count($items);
	
	//IMDB Variables
	$img = '';
	$desc = '';
	$votes = '';
	$year = '';
	$score = '';
	$genres = '';
	$network = '';
	$img = '';
			
	//Lets try set all the imdb vars first
	if (array_key_exists('imdbID',$items[0])) {
		
		$imdbid = $items[0]['imdbID'];
		
		#first lets get the imdb details of this
		$sql = "SELECT * FROM imdbcache where imdbid = '$imdbid'";
		
		$result = $db->prepare($sql);
		$result->execute();
		
		$imdbRow = $result->fetch();
		
		if ($imdbRow) {
			$desc = $imdbRow['desc'];
			if ($imdbRow['year'] != 0) {
				$year = "(" . $imdbRow['year'] . ")";
			}
				
			$score = $imdbRow['score'];
			$votes = $imdbRow['votes'];
			
			if (array_key_exists('posterImg', $imdbRow)) {
			
				if ($imdbRow['posterImg'] != '') {
					$img = "<img src='/images/downloaded/$imdbid.jpg'>";
				}
			}
						
		}
		
	
		if ($imdbRow['genres']) {
			$i = 1;
			foreach (explode('|', $imdbRow['genres']) as $genre) {
				if ($i == 1) {
					$genres = $genres . $genre;
				} else {
					$genres = $genres . " <b>|</b> $genre";
				}
				$i++;
			}

		}
		
	}
			
	if (array_key_exists('tvdbid',$items[0])) {
			
		$tvdbid = $items[0]['tvdbid'];
						
		#first lets get the imdb details of this
		$sql = "SELECT * FROM tvdbcache where tvdbid = '$tvdbid'";
			
		$result = $db->prepare($sql);
		$result->execute();
			
		$tvdbRow = $result->fetch();
		
		if ($tvdbRow) {
			$network = $tvdbRow['network'];
			
			if ($desc == '') {
				$desc = $tvdbRow['desc'];
			}
			
			if ($img == '') {
				if (array_key_exists('posterImg', $tvdbRow)) {
					if ($tvdbRow['posterImg'] != '') {
						$img = "<img src='/images/downloaded/$tvdbid-tvdb.jpg'>";
					}
					
				}
			}
			
			if ($genres == '') {
				$i = 1;
				if (array_key_exists('genres', $tvdbRow)) {
					foreach (explode('|', $tvdbRow['genres']) as $genre) {
						if ($i == 1) {
							$genres = $genres . $genre;
						} else {
							$genres = $genres . " <b>|</b> $genre";
						}
						$i++;
					}
				}

			}
		
		}
	
	}
	
	$scoreAndVotesHtml = '';
	
	if ($score != '') {
		if ($votes != '' ) {
			$scoreAndVotesHtml = "<br><b>Score:</b> $score ($votes votes)";
		} else {
			$scoreAndVotesHtml = "<br><b>Score:</b> $score";
		}
	}
	
	$networkHtml = '';
	if ($network != '') {
		$networkHtml = "<br><b>Network:</b> $network";
	}
	
	$genreHtml = '' ;

	if ($genres != '') {
		$genreHtml = "<br><b>Genre:</b> $genres";
	}
	
	if ($img == '') {
		$img = "<img src='/images/noimg.gif'>";
	}
				
	if ($count == 1) {
		
		$item = $items[0];
		$id = $item['id'];
		$title = $item['title'];
		
		$errors = '';
		
		if ($item['message'] != '') {
			$msg = $item['message'];
			$errors = "<div class='download-error'>$msg</div>";
		}
		
		$percentComplete = getPercentComplete($item['localpath'], $item['remotesize']);

		$progressBar = '';
		
		if ($_GET["t"] != '6' AND $_GET["t"] != '4') {
			$progressBar = "<div class='progressbar'><div class='progressbar_$id'></div>$percentComplete% Complete</div>
			<script>doProgressbar($id, $percentComplete)</script>";
		}
		
		echo "
		<div class='download-item'>
			<div class='left-col'>
				<div style='float:left'><input role='checkbox' type='checkbox' class='item_$id' name='item[]' value='$id'></div>
				<div style='float:right'>$img</div>
				<div style='clear:both'></div>
			</div>
			<div class='right-col'>
				$progressBar
				<b>Title:</b> $title <b>$year</b>
				$scoreAndVotesHtml
				$genreHtml
				$networkHtml
				<p>$desc</p>
				$errors
			</div>
		</div>
		<div style='clear: both;'></div>";
	} else if ($count > 1) {
		
		$title = $array['title'];
	
		echo "
		<div class='download-item'>
			<div class='left-col'>
				<div style='float:left'><input role='checkbox' type='checkbox' class='multiitem_$title' name='multiitem_$title'></div>
				<div style='right'>$img</div>
				<div style='clear:both'></div>
			</div>
			<div class='right-col'>
				<b>Title:</b> $title <b>$year</b>
				$scoreAndVotesHtml
				$genreHtml
				$networkHtml
				<p>$desc</p>
				<div class='multi-items'>Episodes to download" . buildItems($items) . "</div>
			</div>
		</div>
		<div style='clear: both;'></div>";
	}	
	
}

function buildItems($items) {
	
	$html = '';
	
	foreach ($items as $item) {
		$id = $item['id'];
		$title = $item['title'];
		$percentComplete = getPercentComplete($item['localpath'], $item['remotesize']);
		
		$html .= "
				<div class='download-item-small'>
					<span class='inner'><input role='checkbox' type='checkbox' class='item_$id' name='item[]' value='$id'>$title</span>
				</div>";
		
	}
	
	return $html;

}

function doSpecials() {
	include_once '../../includes/TVDB.php';

	global $db;

	echo '<form id="formID">';

	foreach($_GET['id'] as $id) {
		$sql = "SELECT title from download where id=$id";
		$result = $db->query($sql)->fetch();
			
			
		if ($result) {
			$title = $result['title'];

			//Lets make sure we are working with special
			preg_match('/(^.+)\.S[0-9]+/',  $title, $matches);

			if (count($matches) != 1) {
					
				$showname = $matches[1];
				$shows = TV_Shows::search(str_replace('.', ' ', $showname));

				$specials = "<select name='$id'>
								<option value='none'>Choose Matching Episode</option>";

				if (count($shows) > 0) {
					$show = $shows[0];
						
					$eps = $show->getSeason(0);
						
					foreach($eps as $ep) {
						$specials .= "<option value='$ep->number'>$ep->name</option>";

					}
				}

				$specials .= '</select>';

					
				echo "
				<div class='download-item'>
				<div class='left'>$title</div>
				<div class='right'>$specials</div>
				</div>";
			}
		} else {
				continue;
		}
		
	}
	echo '</form>';

}
	
?>
