<?php

	/**
	 * TV shows class, basic searching functionality
	 * 
	 * @package PHP::TVDB
	 * @author Ryan Doherty <ryan@ryandoherty.com>
	 */

	class TV_User extends TVDB {

		/**
		 * Find a tv show by the id from thetvdb.com
		 *
		 * @return TV_Show|false A TV_Show object or false if not found
		 **/
		public static function getFavs($accountid) {
			$params = array('action' => 'get_favs', 'accountid' => $accountid);
			$data = self::request($params);
			
			if ($data) {
				$xml = @simplexml_load_string($data);
				
                if($xml) {
    				return $xml;
                } else {
                    return false;
                }
			} else {
				return false;
			}
		}
		
		public static function deleteFav($id, $accountid) {
			$params = array('action' => 'del_fav', 'id' => "$id", 'accountid' => $accountid);
			$data = self::request($params);
		}
		
		public static function addFav($id, $accountid) {
			$params = array('action' => 'add_fav', 'id' => "$id", 'accountid' => $accountid);
			$data = self::request($params);
		}
	}

?>
