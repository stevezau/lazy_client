<?php

include_once '../../includes/functions.php';

global $db;

switch ($_GET['action']) {
	case "savespecial":
		
		if(is_array($_POST)) {
			foreach($_POST as $id => $epId){
				if ($epId != "none") {
					$sql = "update download set epOverride = $epId, retries = 0, message = '' where id = $id";
					$db->exec($sql);
				}

			}
		}
		echo "success";
		break;
		
	case "delete":
		
		if($_POST['item']){
			foreach($_POST['item'] as $id){
				//delete each $i with $i being the id
				try {
					
					$sql = "SELECT localpath,lftppid from download where id=$id";
					$result = $db->query($sql)->fetch();
					
					if(array_key_exists('lftppid', $result) && $result['lftppid'] != '0' && $result['lftppid'] != '') {
						posix_kill($result['lftppid'], 9);
					}
					
					if(array_key_exists('localpath', $result) && $result['localpath'] != '') {
						$path = $result['localpath'];
						
						if (is_dir($path)) {
							delete($path);				
							} else if (is_file) {
							unlink($path);
						}
						
					}
											
					$sql = "Delete from download where id = " . $id;
					$db->exec($sql);
					
				} catch (PDOException $e) {
					echo "Error deleting id: " . $id . " because " . $e->getMessage(); 
				}
			}
			echo 'Delete Success';
			
		}
		break;
		
		
		case "reset":
		
			if($_POST['item']){
				foreach($_POST['item'] as $id){
					//delete each $i with $i being the id
					try {
							
						$sql = "SELECT localpath,lftppid from download where id=$id";
						$result = $db->query($sql)->fetch();
							
						if(array_key_exists('lftppid', $result) && $result['lftppid'] != '0' && $result['lftppid'] != '') {
							posix_kill($result['lftppid'], 9);
						}
							
							
						$sql = "update download set status = 1 where id = " . $id;
						$db->exec($sql);
							
					} catch (PDOException $e) {
						echo "Error resetting id: " . $id . " because " . $e->getMessage();
					}
				}
				echo 'Reset Success';
					
			}
			break;
			
		
	case "priority":
		if($_POST['item']){
			foreach($_POST['item'] as $id){
				//minus the priorirty by 1
				try {
					$sql = "SELECT priority,title from download where id=$id";
					$result = $db->query($sql)->fetch();
			
					if(!empty($result['priority'])) {
						$pri = $result['priority'];
						$title = $result['title'];
						
						if ($pri > 1) {
							$newpri = $result['priority'] - 1;
							$sql = "UPDATE download set priority = $newpri where id=$id";
							$db->exec($sql);
							
							echo "$title new priority: $newpri<br>";								
						} else {
							echo "$title already at highest priority";
						}
						
					}
					
	
				} catch (PDOException $e) {
					echo "Some error setting priroirty id: " . $id . " because " . $e->getMessage();
				}
			}					
		}
		break;
		
	case "approve":
		if($_POST['item']){
			foreach($_POST['item'] as $id){
				//approve each $i with $i being the id
				try {
					$sql = "update download set status = 1 where id = " . $id;
					$result = $db->prepare($sql);
					$result->execute();
	
				} catch (PDOException $e) {
					echo "Error approving id: " . $id . " because " . $e->getMessage();
				}
			}
			echo 'Approve Success';
				
		}
		break;
		
		
	case "retry":
		global $config;
			if($_POST['item']){
				foreach($_POST['item'] as $id){
					//approve each $i with $i being the id
					try {
						$sql = "update download set retries = 0, message = 'Retrying extraction' where id = " . $id;
						$result = $db->prepare($sql);
						$result->execute();
		
					} catch (PDOException $e) {
						echo "Error approving id: " . $id . " because " . $e->getMessage();
					}
				}
		
				$lazyCmd = $config::$lazy_exec;
				$command = "$lazyCmd moverls";
			
				execInBackground($command);
				echo 'Reset Success';
			
			}
			break;
			
	case "approvemore":
		if($_POST['item']){
			foreach($_POST['item'] as $id){
				try {
					$sql = "SELECT title,tvdbid from download where id=$id";
					$result = $db->query($sql)->fetch();
					
					$title = $result['title'];
					
					if (array_key_exists('tvdbid', $result) && $result['tvdbid'] != '') {
						//lets add it to tvdb favs
						include_once '../../includes/TVDB.php';
						$tvdbusr = new TV_User();
						
						$tvdbusr->addFav($result['tvdbid']);
						
						echo "Added $title to THETVDB Favs<br>";
					} else {
						//Now add to the approve list
						$title = preg_replace('/\.S[0-9][0-9]E[0-9][0-9].+/i', '', $title);
						addToFile($title, '/home/media/.flexget/approve.yml');
						echo "Show $title has no TVDB ID Set so it was added to manual approve<br>";
					
					}
					
					$sql = "update download set status = 1 where id = " . $id;
					$db->exec($sql);										
					
					
				} catch (PDOException $e) {
					echo "Error adding to approval list id: " . $id . " because " . $e->getMessage() . "<br>";
				}
			}
			echo 'Approve Success';
			
		}
		break;
	case "ignore":
		if($_POST['item']){
			foreach($_POST['item'] as $id){
				$sql = "SELECT title from download where id=$id";
				$result = $db->query($sql)->fetch();
				
				if(!empty($result['title'])) {
					$title = preg_replace('/\.S[0-9][0-9]E[0-9][0-9].+/i', '', $result['title']);
					addToFile($title, '/home/media/.flexget/ignore.yml');
					
					$sql = "DELETE from download where id=$id";
					$db->exec($sql);
				}
				
			}
			echo "Ignore Success";
		}
		break;
	default:
		echo 'UNKNWON COMMAND';
}
?>